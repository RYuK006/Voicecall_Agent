# Using Your Personal Phone Number for Outbound AI Calls

Can you use your own phone number to call people, or reroute calls through your SIM? **Yes!** There are two distinct methods depending on whether you want your number to show up on their caller ID or if you want to use your SIM card's free mobile minutes.

---

## Method 1: Verified Caller ID (Cloud Gateway Route) — Recommended

If you want the call to come from a server, but **your personal mobile number appears on the recipient's screen**:

```
[FastAPI AI Server] ──> [Telephony Gateway (Twilio/Plivo)] ──> [Recipient Phone]
                                    │
                  (Displays YOUR verified mobile number)
```

### How It Works:
1. When using a provider like **Twilio** or **Exotel**, you don't have to buy a random virtual number.
2. You can register your personal mobile number (e.g., `+91 8075985482`) as a **Verified Outgoing Caller ID** by completing a quick OTP verification.
3. When the AI initiates a phone call, the telephony provider injects your number as the `From` header.
4. **What the recipient sees:** Their phone rings and displays **your name/photo and your personal phone number**. If they call back, it rings directly on your personal phone!

### Cost:
* Uses Twilio's $15 free trial credits to dial real verified numbers.

---

## Method 2: Android Phone as a Local GSM Gateway (Using Your Physical SIM Plan)

If you have an Indian mobile plan (Jio / Airtel / Vi) with **free unlimited calls** and want **₹0 telephony costs**:

```
[Windows PC (AI Agent)] 
        │ (Bluetooth Hands-Free Profile / Virtual Audio Cable)
[Android Smartphone (Your Physical SIM)]
        │ (Cellular GSM Network - Free Carrier Minutes)
[Recipient Phone]
```

### How It Works:
1. **The Web Dashboard & Server Run on Your Laptop**:
   - You open `http://localhost:8000` in Chrome/Edge on your **laptop**.
   - Your laptop acts as the brain (LLM, speech recognition, neural TTS synthesis).
2. **Bluetooth Headset Emulation (Zero Phone Mic Usage)**:
   - Your laptop connects to your Android phone via Bluetooth as a **Hands-Free Audio Gateway (HFP/SCO)**.
   - An Android phone cannot be a hands-free headset to itself; it only routes call audio digitally over Bluetooth when connected to an external device (your laptop).
   - This bypasses and mutes the phone's physical microphone completely.
3. **Automated Dialing via ADB**:
   - A lightweight ADB command or Android service triggers the call:
   ```bash
   adb shell am start -a android.intent.action.CALL -d tel:+919876543210
   ```
4. **The Phone Acts as a Cellular Modem**:
   - Your phone just sits on the desk. The call goes out through your physical SIM card.
   - It costs **₹0 in carrier API fees** because it consumes your mobile recharge pack's unlimited talk-time!

---

## Comparison Summary

| Feature | Method 1: Verified Caller ID (Twilio) | Method 2: Android Phone as GSM Gateway |
|---|---|---|
| **Displays Your Number?** | ✅ Yes (Exact personal number) | ✅ Yes (Made directly from your SIM) |
| **Call Bill / Telecom Cost** | Uses trial credits (~₹0.40/min in bulk) | **₹0.00** (Uses your free SIM plan) |
| **Hardware Required** | None (Runs purely in software) | Android phone connected via Bluetooth / USB |
| **Setup Complexity** | Very simple (1 API key + OTP verification) | Medium (Bluetooth audio bridging) |
| **Scalability** | Can make 10-50 simultaneous calls | 1 call at a time per smartphone |
