#!/usr/bin/env python3
"""
Termux SIM Dialing Bridge
Runs directly inside Termux on Android.
Listens for HTTP dial and call status commands from the laptop over local Wi-Fi.
Zero dependencies: Uses only Python standard library.
"""

import http.server
import socketserver
import json
import subprocess
import socket
import re
import shutil
import sys
import os

PORT = int(os.getenv("BRIDGE_PORT", "8080"))

def get_local_ip():
    """Get the phone's local Wi-Fi IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def get_telephony_state():
    """Check dumpsys telecom or telephony.registry for call state."""
    try:
        # 1. dumpsys telecom (gold standard for active vs dialing)
        res = subprocess.run(["dumpsys", "telecom"], capture_output=True, text=True, timeout=3)
        out = res.stdout
        if re.search(r"mCalls:\s*.*\[TC@\d+,\s*ACTIVE\b", out, re.DOTALL) or re.search(r"Foreground call:\s*\[TC@\d+,\s*ACTIVE\b", out):
            return {"state": "active", "answered": True}
        if re.search(r"mCalls:\s*.*\[TC@\d+,\s*(DIALING|CONNECTING)\b", out, re.DOTALL) or re.search(r"Foreground call:\s*\[TC@\d+,\s*(DIALING|CONNECTING)\b", out):
            return {"state": "dialing", "answered": False}
        if re.search(r"mCalls:\s*.*\[TC@\d+,\s*RINGING\b", out, re.DOTALL) or re.search(r"Foreground call:\s*\[TC@\d+,\s*RINGING\b", out):
            return {"state": "ringing", "answered": False}
        if re.search(r"mCalls:\s*.*\[TC@\d+,\s*DISCONNECTED\b", out, re.DOTALL):
            return {"state": "idle", "answered": False}
        if "mCalls:\n    none" in out or "mCalls: []" in out or ("mCalls:" in out and "[TC@" not in out):
            return {"state": "idle", "answered": False}
    except Exception:
        pass

    try:
        # 2. dumpsys telephony.registry
        res = subprocess.run(["dumpsys", "telephony.registry"], capture_output=True, text=True, timeout=3)
        out = res.stdout
        fg_match = re.search(r"mForegroundCallState\s*[=:]\s*(\d+)", out)
        if fg_match:
            fg_val = fg_match.group(1)
            if fg_val == "3":
                return {"state": "active", "answered": True}
            elif fg_val in ("1", "2"):
                return {"state": "dialing", "answered": False}
            elif fg_val == "0":
                return {"state": "idle", "answered": False}
        match = re.search(r"mCallState\s*[=:]\s*(\d+)", out)
        if match:
            val = match.group(1)
            if val == "0":
                return {"state": "idle", "answered": False}
            elif val == "1":
                return {"state": "ringing", "answered": False}
            elif val == "2":
                return {"state": "active", "answered": True}
    except Exception:
        pass

    return {"state": "unknown", "answered": False}

class BridgeHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({"status": "ok"})

    def do_GET(self):
        if self.path == "/ping" or self.path == "/":
            self._send_json({"status": "ok", "service": "termux-sim-bridge"})
        elif self.path == "/status":
            state = get_telephony_state()
            self._send_json(state)
        else:
            self._send_json({"status": "error", "message": "Not found"}, 404)

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(post_data) if post_data else {}
        except Exception:
            payload = {}

        if self.path == "/dial":
            phone = payload.get("phone", "")
            clean_number = "".join(c for c in phone if c.isdigit() or c == "+")
            if not clean_number:
                self._send_json({"status": "error", "message": "Invalid phone number"}, 400)
                return

            # Dial via termux-telephony-call or am start
            success = False
            err_msg = ""
            if shutil.which("termux-telephony-call"):
                res = subprocess.run(["termux-telephony-call", clean_number], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    success = True
                else:
                    err_msg = res.stderr

            if not success:
                res = subprocess.run(["am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{clean_number}"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    success = True
                else:
                    err_msg = res.stderr or err_msg

            if success:
                print(f"[Bridge] Dialing {clean_number}...")
                self._send_json({"status": "ok", "message": f"Dialing {clean_number} via Termux SIM"})
            else:
                self._send_json({"status": "error", "message": err_msg or "Failed to trigger call"}, 500)

        elif self.path == "/hangup":
            subprocess.run(["input", "keyevent", "6"], capture_output=True, text=True, timeout=3)
            print("[Bridge] Hang up signal sent.")
            self._send_json({"status": "ok", "message": "Call ended"})
        else:
            self._send_json({"status": "error", "message": "Not found"}, 404)

    def log_message(self, format, *args):
        sys.stderr.write(f"[Termux Bridge] {format % args}\n")

if __name__ == "__main__":
    local_ip = get_local_ip()
    print("=" * 60)
    print("📱 Termux SIM Dialing Bridge Started!")
    print("=" * 60)
    print(f"Phone Wi-Fi IP Address: http://{local_ip}:{PORT}")
    print("\nOn your laptop:")
    print(f"1. Set in .env or enter in Dashboard:")
    print(f"   TERMUX_BRIDGE_URL=http://{local_ip}:{PORT}")
    print("2. Keep this Termux window open in background.")
    print("=" * 60)
    
    with socketserver.ThreadingTCPServer(("", PORT), BridgeHandler) as httpd:
        httpd.serve_forever()
