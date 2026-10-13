import io
import base64
import edge_tts
from typing import Optional, Tuple
from app.config import VOICE_MAPPINGS, DEFAULT_LANG, DEFAULT_GENDER

class TTSEngine:
    """Ultra-realistic, free Text-to-Speech synthesis using Microsoft Edge Neural Voices."""

    @classmethod
    def get_voice_for(cls, lang_code: str = DEFAULT_LANG, gender: str = DEFAULT_GENDER) -> str:
        lang_data = VOICE_MAPPINGS.get(lang_code.lower())
        if not lang_data:
            # Fallback to Hindi or Indian English
            lang_data = VOICE_MAPPINGS.get("hi", VOICE_MAPPINGS["en"])
        return lang_data.get(gender.lower(), lang_data["female"])

    @classmethod
    async def synthesize_to_bytes(
        cls,
        text: str,
        lang_code: str = DEFAULT_LANG,
        gender: str = DEFAULT_GENDER,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bytes:
        """Synthesize text to MP3 audio bytes asynchronously."""
        voice = cls.get_voice_for(lang_code, gender)
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
                
        return audio_stream.getvalue()

    @classmethod
    async def synthesize_to_base64(
        cls,
        text: str,
        lang_code: str = DEFAULT_LANG,
        gender: str = DEFAULT_GENDER,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> str:
        """Synthesize text to Base64 encoded MP3 string for WebSockets/JSON transport."""
        audio_bytes = await cls.synthesize_to_bytes(text, lang_code, gender, rate, pitch)
        return base64.b64encode(audio_bytes).decode("utf-8")
