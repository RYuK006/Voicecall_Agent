# Architecture & Design Decision

## Selected Path: 100% Free Voice Agent Prototype
- **Goal**: Replicate the Sarvam AI RSVP Voice Agent workflow completely free of cost (₹0 bills).
- **Core Workflow**:
  1. User initiates a call via interactive Web/Audio interface.
  2. Voice input captured in real-time.
  3. Real-time Speech-to-Text (STT) transcribe Indic/English speech.
  4. Conversational Agent (LLM) prompts the guest about event attendance, guest count, dietary preferences, or questions.
  5. Natural Text-to-Speech (TTS) synthesizes conversational voice responses in Hindi / Malayalam / English.
  6. RSVP status and responses automatically update a mock CRM / Google Sheet / Local Database.

## Technology Stack Decision
- **Backend Runtime**: Python (FastAPI + WebSockets for bi-directional audio streaming)
- **STT (Speech-to-Text)**: Hybrid STT: Zero-latency browser Web Speech API for real-time transcription supporting Hindi (`hi-IN`), Malayalam (`ml-IN`), and Indian English (`en-IN`), with server-side Whisper audio chunk fallback.
- **Conversational Intelligence (LLM)**: Hybrid Engine: Supports Google Gemini 2.5 Flash / Groq free tier when keys are provided, and includes a built-in intelligent zero-config Indic/English conversational fallback engine that runs 100% locally with zero setup or API keys required.
- **TTS (Text-to-Speech)**: Microsoft Edge-TTS (Free, ultra-natural neural voices for Hindi, Malayalam, Indian English)
- **Audio Transport**: Low-latency WebSocket streaming with PCM/WAV/MP3 audio chunks
- **Management & UI**: Interactive Web Dashboard with visual audio waves, live conversation transcripts, event editor, and CSV / Google Sheets two-way sync
- **RSVP Tracking**: Automatic structured extraction (Attendance status: Attending / Declined / Tentative, Guest Count, Dietary preferences, Notes)


