# Indic Voice Call Agent 🎙️

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Cost](https://img.shields.io/badge/Cost-₹0%20(100%25%20Free)-success.svg)](#cost-analysis-vs-sarvam-ai)
[![Python](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)

A **100% Free, Zero-Billing Indic Conversational Voice Agent** for automated event RSVPs, customer confirmations, and telephony campaigns. Built as a zero-cost alternative to paid voice platforms like Sarvam AI.

---

## 🎯 Cost Analysis vs. Sarvam AI

Based on the official [Sarvam Voice Agent documentation](https://docs.sarvam.ai/voice-agents/pricing.md) and Notion specifications:

| Component | Sarvam AI Official Platform | Our Architecture |
|---|---|---|
| **Voice Agent Pipeline (STT + LLM + TTS)** | **₹3.50 / minute** (billed in 60s pulses) | **₹0.00 / minute** (100% Free) |
| **Simulated Testing** | **₹2.00 / test run** | **₹0.00** (Unlimited free testing) |
| **Telephony Gateway** | **₹0.20 per 30s pulse** (~₹0.40/min) | **₹0.00** via WebRTC/Browser Audio |
| **Virtual DID Phone Number** | **₹59 / 30 days** rental | **₹0.00** |
| **Languages Supported** | 11 Indian Languages + English | **11 Indian Languages** (Hindi, Malayalam, English, Bengali, Tamil, Telugu, Marathi, etc.) |
| **Monthly Subscription** | ₹0 (Pay-as-you-go) up to ₹49,999/mo | **₹0 Forever** |

> **Conclusion:** Sarvam AI **cannot** be operated permanently free of cost. This repository delivers an end-to-end, production-grade equivalent that runs at **zero cost**!

---

## 🏗️ Architecture

```
                 [ Browser / Web Audio Client ]
                   │                        ▲
       Web Speech  │                        │ Edge-TTS Neural Audio
       STT Stream  ▼                        │ (Base64 / MP3)
                 [ FastAPI + WebSocket Gateway ]
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
     [ Conversational Agent ]          [ RSVP Manager ]
     ├── Indic Intent Parser           ├── Guest Directory
     ├── Tech Summit 2026 Context      ├── Real-Time Headcounts
     └── Hybrid LLM Engine             └── Google Sheets CSV Sync
         ├── Gemini 2.5 Flash (Free)
         ├── Groq Llama 3 (Free)
         └── Zero-Config Local Rules
```

---

## 🚀 Key Features

1. **Natural Indic Neural Speech Synthesis (Edge-TTS)**:
   - **Hindi (`hi-IN`)**: *Swara* (Female) & *Madhur* (Male)
   - **Malayalam (`ml-IN`)**: *Sobhana* (Female) & *Midhun* (Male)
   - **Indian English (`en-IN`)**: *Neerja* & *Prabhat*
   - Also supports Tamil, Telugu, Bengali, and Marathi.
2. **Zero-Latency Conversational Engine**:
   - Understands code-mixing (Hinglish & Manglish).
   - Accurately parses confirmations, declines, tentative responses, plus-ones (headcounts), and dietary restrictions.
   - Built-in FAQ responder for venue, parking, timing, and virtual streaming.
3. **Interactive Web Dashboard**:
   - Outbound call simulation with dancing audio waveforms and visual avatar pulses.
   - Live real-time call transcript stream.
   - Event settings editor.
   - One-click guest calling and RSVP status table.
   - CSV export compatible with Google Sheets & Make.com.
4. **Hybrid Intelligence**:
   - Works immediately out of the box with zero configuration or API keys.
   - Optionally connect free Google Gemini or Groq API keys for custom open-ended LLM dialogues.

---

## 💻 Quick Start

### 1. Clone & Navigate
```bash
git clone https://github.com/RYuK006/Voicecall_Agent.git
cd Voicecall_Agent
```

### 2. Install Dependencies
```bash
py -m pip install -r requirements.txt
```

### 3. Launch Server
```bash
py main.py
```
Open **[http://localhost:8000](http://localhost:8000)** in Google Chrome or Microsoft Edge.

---

## 📁 Repository Structure

```
Voicecall_Agent/
├── app/
│   ├── config.py             # Voice mappings & environment settings
│   ├── agent.py              # Conversational logic & Indic RSVP intent engine
│   ├── tts.py                # Asynchronous Edge-TTS voice synthesis
│   ├── rsvp_manager.py       # Guest directory & CSV synchronization
│   └── server.py             # FastAPI REST & WebSocket streaming server
├── static/
│   ├── index.html            # Dashboard and live voice call UI
│   ├── style.css             # Glassmorphism dark styling & audio wave animations
│   └── app.js                # Web Speech STT, audio decoder, and WebSocket logic
├── data/
│   ├── event_config.json     # Tech Conference & AI Summit 2026 details
│   ├── guests.json           # Sample RSVP guest database
│   └── rsvps.csv             # Exportable spreadsheet
├── ARCHITECTURE.md           # Architecture specifications & design decisions
├── RESEARCH_AND_FEASIBILITY.md # Detailed Sarvam cost research
├── main.py                   # Server launcher
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation
```

---

## 👤 Author
- **Contributor**: [RYuK006](https://github.com/RYuK006)
