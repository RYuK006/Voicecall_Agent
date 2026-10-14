import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.config import STATIC_DIR, RSVP_CSV_PATH, DEFAULT_LANG, DEFAULT_GENDER
from app.rsvp_manager import RSVPManager
from app.tts import TTSEngine
from app.agent import ConversationalAgent
from app.gsm_dialer import GSMDialer

app = FastAPI(title="Indic Voice Call Agent", version="1.0.0")

# Mount static directory for frontend
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Voicecall Agent API running. Open /static/index.html"}

@app.get("/api/event")
async def get_event():
    return RSVPManager.get_event_config()

@app.post("/api/event")
async def save_event(config: Dict[str, Any]):
    success = RSVPManager.save_event_config(config)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save event configuration")
    return {"status": "ok", "config": config}

@app.get("/api/keys")
async def get_keys_status():
    import app.config as cfg
    return {
        "has_grok": bool(cfg.XAI_GROK_API_KEY),
        "has_groq": bool(cfg.GROQ_API_KEY),
        "has_gemini": bool(cfg.GEMINI_API_KEY),
        "active_engine": "xAI Grok" if cfg.XAI_GROK_API_KEY else ("Groq Llama 3" if cfg.GROQ_API_KEY else ("Gemini Flash" if cfg.GEMINI_API_KEY else "Local Fallback Rules"))
    }

class KeysUpdateRequest(BaseModel):
    grok_key: Optional[str] = ""
    gemini_key: Optional[str] = ""

@app.post("/api/keys")
async def update_keys(req: KeysUpdateRequest):
    import app.config as cfg
    env_lines = []
    
    if req.grok_key:
        k = req.grok_key.strip()
        if k.startswith("xai-"):
            cfg.XAI_GROK_API_KEY = k
            env_lines.append(f"XAI_GROK_API_KEY={k}\nGROK_API_KEY={k}\n")
        else:
            cfg.GROQ_API_KEY = k
            env_lines.append(f"GROQ_API_KEY={k}\nGROK_API_KEY={k}\n")
    if req.gemini_key:
        k = req.gemini_key.strip()
        cfg.GEMINI_API_KEY = k
        env_lines.append(f"GEMINI_API_KEY={k}\n")

    env_path = cfg.BASE_DIR / ".env"
    with open(env_path, "a", encoding="utf-8") as f:
        f.writelines(env_lines)

    return await get_keys_status()

@app.get("/api/guests")
async def get_guests():
    return RSVPManager.get_guests()

@app.post("/api/guests")
async def add_or_update_guest(guest: Dict[str, Any]):
    saved = RSVPManager.add_guest(guest)
    return {"status": "ok", "guest": saved}

@app.get("/api/stats")
async def get_stats():
    return RSVPManager.get_stats()

@app.get("/api/export-csv")
async def export_csv():
    if not RSVP_CSV_PATH.exists():
        RSVPManager._export_to_csv_unlocked(RSVPManager.get_guests())
    return FileResponse(RSVP_CSV_PATH, filename="rsvps.csv", media_type="text/csv")

class DialRequest(BaseModel):
    phone: str

@app.post("/api/dial-sim")
async def dial_sim_number(req: DialRequest):
    result = GSMDialer.dial(req.phone)
    return result

@app.post("/api/end-sim")
async def end_sim_call():
    result = GSMDialer.end_call()
    return result

@app.get("/api/sim-call-status")
async def get_sim_call_status():
    info = GSMDialer.get_detailed_call_state()
    return info

class TTSRequest(BaseModel):
    text: str
    lang: Optional[str] = DEFAULT_LANG
    gender: Optional[str] = DEFAULT_GENDER

@app.post("/api/tts")
async def synthesize_speech(req: TTSRequest):
    try:
        audio_base64 = await TTSEngine.synthesize_to_base64(
            text=req.text,
            lang_code=req.lang,
            gender=req.gender
        )
        return {"status": "ok", "audio_base64": audio_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/call")
async def websocket_call_endpoint(websocket: WebSocket):
    """Real-time bi-directional voice call session."""
    await websocket.accept()

    # Session state
    agent: Optional[ConversationalAgent] = None
    lang: str = DEFAULT_LANG
    gender: str = DEFAULT_GENDER
    guest_id: Optional[str] = None

    try:
        # Wait for handshake or initialization message
        init_data_raw = await websocket.receive_text()
        init_data = json.loads(init_data_raw)

        guest_id = init_data.get("guest_id")
        lang = init_data.get("lang", DEFAULT_LANG)
        gender = init_data.get("gender", DEFAULT_GENDER)

        guest = None
        if guest_id:
            guest = RSVPManager.find_guest(guest_id)
        
        agent = ConversationalAgent(guest=guest, lang=lang)

        # Generate and synthesize initial greeting
        greeting_text = agent.get_greeting()
        audio_b64 = await TTSEngine.synthesize_to_base64(
            text=greeting_text,
            lang_code=lang,
            gender=gender
        )

        await websocket.send_json({
            "type": "agent_speech",
            "text": greeting_text,
            "audio_base64": audio_b64,
            "guest": agent.guest
        })

        # Process conversation loop
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)

            msg_type = data.get("type")

            if msg_type == "user_speech":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                # Notify client that agent is thinking
                await websocket.send_json({"type": "agent_thinking"})

                # Generate conversational response
                agent_response, rsvp_update, is_closing = await agent.generate_response(user_text)

                # Synthesize neural voice audio
                audio_b64 = await TTSEngine.synthesize_to_base64(
                    text=agent_response,
                    lang_code=lang,
                    gender=gender
                )

                # Send back agent response & updated RSVP state
                await websocket.send_json({
                    "type": "agent_speech",
                    "text": agent_response,
                    "audio_base64": audio_b64,
                    "rsvp_update": rsvp_update,
                    "guest": agent.guest,
                    "is_closing": is_closing
                })

            elif msg_type == "change_lang":
                lang = data.get("lang", lang)
                agent.lang = lang
                await websocket.send_json({
                    "type": "system_info",
                    "message": f"Language switched to {lang}"
                })

            elif msg_type == "hangup":
                await websocket.send_json({"type": "call_ended"})
                break

    except WebSocketDisconnect:
        print(f"Call disconnected: guest={guest_id}")
    except Exception as e:
        print(f"Error in websocket call session: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
