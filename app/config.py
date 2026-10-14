import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

EVENT_CONFIG_PATH = DATA_DIR / "event_config.json"
GUESTS_FILE_PATH = DATA_DIR / "guests.json"
RSVP_CSV_PATH = DATA_DIR / "rsvps.csv"

# Voice mappings for Microsoft Edge-TTS (100% Free, High Quality Neural)
VOICE_MAPPINGS = {
    "hi": {
        "female": "hi-IN-SwaraNeural",
        "male": "hi-IN-MadhurNeural",
        "name": "Hindi",
        "locale": "hi-IN"
    },
    "ml": {
        "female": "ml-IN-SobhanaNeural",
        "male": "ml-IN-MidhunNeural",
        "name": "Malayalam",
        "locale": "ml-IN"
    },
    "en": {
        "female": "en-IN-NeerjaNeural",
        "male": "en-IN-PrabhatNeural",
        "name": "Indian English",
        "locale": "en-IN"
    },
    "ta": {
        "female": "ta-IN-PallaviNeural",
        "male": "ta-IN-ValluvarNeural",
        "name": "Tamil",
        "locale": "ta-IN"
    },
    "te": {
        "female": "te-IN-ShrutiNeural",
        "male": "te-IN-MohanNeural",
        "name": "Telugu",
        "locale": "te-IN"
    },
    "bn": {
        "female": "bn-IN-TanishaaNeural",
        "male": "bn-IN-BashkarNeural",
        "name": "Bengali",
        "locale": "bn-IN"
    },
    "mr": {
        "female": "mr-IN-AarohiNeural",
        "male": "mr-IN-ManoharNeural",
        "name": "Marathi",
        "locale": "mr-IN"
    }
}

DEFAULT_LANG = "hi"
DEFAULT_GENDER = "female"

# Cloud AI API Keys (Optional - System works 100% offline/locally if not provided)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "") or os.getenv("GROK_API_KEY", "")
XAI_GROK_API_KEY = os.getenv("XAI_GROK_API_KEY", "") or os.getenv("XAI_API_KEY", "") or (os.getenv("GROK_API_KEY", "") if os.getenv("GROK_API_KEY", "").startswith("xai-") else "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Digital Telephony Carrier Configuration (Optional for 100% microphone-free cloud calling)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_VERIFIED_CALLER_ID = os.getenv("TWILIO_VERIFIED_CALLER_ID", "")

# Server configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
