# Running the AI Voice Agent Directly on Your Android Phone & GSM SIM Setup

Can you run all of this directly on your phone? **Yes!** Android is powered by Linux, which allows the entire Python server, WebSocket audio pipeline, Edge-TTS speech engine, and dashboard to run locally on your mobile device.

---

## 📱 Part 1: How to Run the Whole System Standalone on Your Phone (via Termux)

You don't need a PC running 24/7. Your smartphone's CPU and RAM are powerful enough to host the server and serve the dashboard.

### Step 1: Install Termux on Your Android Phone
1. Download and install **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) (do not use Google Play Store, as the Play Store build is deprecated).
2. Also install **Termux:API** from F-Droid (for telephony and phone dialing permissions).

### Step 2: Set Up the Python Environment
Open Termux and execute:
```bash
# Update repositories
pkg update -y && pkg upgrade -y

# Install Python, Git, and build tools
pkg install python git clang -y

# Install Termux API tools
pkg install termux-api -y

# Clone your repository
git clone https://github.com/RYuK006/Voicecall_Agent.git
cd Voicecall_Agent

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Start the Server on Your Phone
```bash
python main.py
```
* Open **Google Chrome** on your phone.
* Navigate to **`http://localhost:8000`**.
* The entire interactive voice call dashboard and RSVP management system will be running right on your phone!

---

## 📞 Part 2: How Calling Through Your Physical SIM Card Works

When you want the AI to place phone calls using your SIM card's free unlimited calling pack (Jio / Airtel / Vi), there is a key Android OS detail to understand:

> **Android Security Architecture:**  
> In modern Android, the cellular baseband modem (the chip handling physical SIM calls) is strictly sandboxed from user-space apps for user privacy. Ordinary apps cannot quietly inject fake audio into a regular cellular phone call without specific routing.

To bridge the AI voice into your cellular SIM calls, you have two proven methods:

### Method A: PC + Phone via Bluetooth Hands-Free (Easiest & Cleanest)
* **Setup**: Pair your Windows PC and your Android phone via Bluetooth as an **Audio / Hands-Free Device** (just like a car stereo or wireless headset).
* **The Flow**:
  1. Click **"Call via SIM"** on the dashboard.
  2. The server fires an ADB command:
     ```bash
     adb shell am start -a android.intent.action.CALL -d tel:+919876543210
     ```
  3. The phone dials out through your SIM card using your free minutes.
  4. The phone treats your PC as its Bluetooth headset:
     - The PC's speakers output into the call (Edge-TTS AI voice).
     - The PC's microphone captures the other person's voice from the call.
  5. **Cost**: **₹0.00**.

### Method B: 100% On-Device Standalone Calling
If the phone is running everything inside Termux without any PC attached:
* **Dialing**: Handled by Termux-API:
  ```bash
  termux-telephony-call +919876543210
  ```
* **Audio Routing Options**:
  1. **Speakerphone Acoustic Mode**: The phone places the call on speakerphone; the background agent listens and speaks via the speakerphone stream.
  2. **USB-C / 3.5mm Hardware Audio Loopback**: A $3 USB-C / TRRS splitter loopback cable connects output audio directly into the mic input.
  3. **Root / Magisk Audio HAL Module** (if phone is rooted): Directly unlocks bidirectional in-call voice routing.

---

## Summary of Next Steps
* To run the server on your phone: install **Termux**, clone `RYuK006/Voicecall_Agent`, and run `python main.py`.
* To test cellular calling immediately with your SIM card: pair your phone to PC via Bluetooth, and click **"Call via SIM"**.
