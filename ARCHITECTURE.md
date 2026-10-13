# Architecture & Design Decision

## Selected Path: 100% Free Voice Agent Prototype
- **Goal**: Replicate the Sarvam AI RSVP Voice Agent workflow completely free of cost (₹0 bills).
- **Core Workflow**:
  1. User initiates a call via interactive Web/Audio interface.
  2. Voice input captured in real-time.
  3. Real-time Speech-to-Text (STT) transcribe Indic/English speech.
  4. Conversational Agent (LLM) prompts the guest about event attendance, guest count, dietary preferences, or questions.
  5. Natural Text-to-Speech (TTS) synthesizes conversational voice responses in Hindi / English / regional languages.
  6. RSVP status and responses automatically update a mock CRM / Google Sheet / Local Database.
