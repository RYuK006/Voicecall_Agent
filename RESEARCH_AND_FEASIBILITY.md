# Sarvam Voice Agent: Research & Cost Feasibility Analysis

## 1. Project Overview & Architecture
Based on the Notion specification (**"Sarvam Voice Agents Setup: Build an AI Calling Agent in 30 Minutes"**), the system implements an outbound/inbound conversational voice agent designed for event RSVPs and follow-ups:

```
[RSVP Google Sheet / CRM] 
        │
        ▼ (Make.com / Webhook)
[Sarvam Voice Agent Platform (Samvaad / Genie)]
   ├── Indic STT (Saarika v2)
   ├── Conversational LLM (Prompt & Event Context)
   └── Indic TTS (Bulbul v2 - Hindi / 11 Indian Languages + Hinglish)
        │
        ▼ (SIP / Telephony Gateway: Vobiz, Twilio, Plivo, Exotel)
[Recipient Phone / GSM Network]
```

---

## 2. Can You Do This For Free of Cost?

### **Direct Answer:**
**No, you cannot build and operate this completely free of cost using Sarvam's official Voice Agent platform.**

### **Detailed Cost Breakdown**

| Component | Provider / Tool | Cost | Is There a Free Tier? |
|---|---|---|---|
| **Voice Agent Pipeline (STT + LLM + TTS)** | Sarvam AI (Samvaad) | **₹3.50 / minute** (billed in 60s pulses, rounded up) | ❌ **No Free Tier** for Voice Agents. |
| **Simulated Testing** | Sarvam Platform | **₹2.00 / test run** | ❌ No free testing runs. |
| **Telephony Gateway (Calling)** | Sarvam Telephony (via Vobiz) | **₹0.20 per 30-sec pulse** (~₹0.40 / min) | ❌ Standard telecom carrier charges apply. |
| **Virtual DID Phone Number** | Sarvam / Vobiz | **₹59 / 30 days** per phone number | ❌ Phone numbers require monthly rental. |
| **RSVP Automation** | Make.com | Free up to 1,000 operations/month | ✅ Free tier available (or custom free Python webhook). |

---

## 3. Are There Any Free Credits or Workarounds?

### A. Free Developer Sign-Up Credits (Limited Initial Trial)
* **Sarvam AI Developer Dashboard:** When you create an account on `sarvam.ai`, you may receive initial one-time promotional wallet credits (typically ₹100 - ₹500) for testing raw APIs (Speech-to-Text, Text-to-Speech, LLM). This allows **15 to 30 minutes of test calls**, but it is not permanently free.
* **Sarvam Startup Program:** Offers 6-12 months of extended credits for qualifying early-stage startups building vernacular products.

### B. Free Alternatives (If the goal is ₹0 Cost)
If you want a **100% Free** voice agent solution, here are alternative architectures:

1. **Web-Based Voice Agent (Browser / App Call) — 100% Free:**
   * **Telephony:** None (Calls take place directly in the browser/app over WebRTC / Web Audio).
   * **STT:** Whisper (via Groq Free Tier API or local Faster-Whisper).
   * **LLM:** Groq Llama 3 / Google Gemini 2.5 Flash (Free Tier).
   * **TTS:** Microsoft Edge-TTS (`edge-tts` Python library - supports natural Indian English & Hindi voices for free).
   * **Total Cost:** **₹0.00**.

2. **Telephony Phone Call with Trial Credits:**
   * **Telephony:** Twilio Free Trial ($15 trial credit) to dial phone numbers.
   * **Orchestration:** Self-hosted Pipecat or LiveKit (LiveKit Cloud has a free tier of 50 GB/month).
   * **Total Cost:** **₹0.00 initially until trial credits expire**.
