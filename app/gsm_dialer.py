import subprocess
import shutil
import sys
from typing import Dict, Any

class GSMDialer:
    """Manages cellular SIM dialing via Android ADB (from PC) or Termux-API (directly on phone)."""

    @classmethod
    def is_termux(cls) -> bool:
        """Detect if running directly inside Termux on Android."""
        return shutil.which("termux-telephony-call") is not None

    @classmethod
    def is_adb_available(cls) -> bool:
        """Detect if ADB is installed and reachable from PC."""
        return shutil.which("adb") is not None

    @classmethod
    def dial(cls, phone_number: str) -> Dict[str, Any]:
        """Trigger an outbound cellular phone call through the phone's physical SIM card."""
        clean_number = "".join(c for c in phone_number if c.isdigit() or c == "+")
        if not clean_number:
            return {"status": "error", "message": "Invalid phone number"}

        # 1. If running standalone on Android inside Termux:
        if cls.is_termux():
            try:
                cmd = ["termux-telephony-call", clean_number]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    return {"status": "ok", "mode": "termux", "message": f"Dialing {clean_number} via Termux SIM"}
                return {"status": "error", "message": res.stderr}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # 2. If running on PC connected to Android phone via ADB:
        if cls.is_adb_available():
            try:
                cmd = [
                    "adb", "shell", "am", "start",
                    "-a", "android.intent.action.CALL",
                    "-d", f"tel:{clean_number}"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    return {"status": "ok", "mode": "adb", "message": f"Dialing {clean_number} via Android ADB"}
                return {"status": "error", "message": res.stderr}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        return {
            "status": "simulated",
            "message": f"Neither ADB nor Termux detected. Simulated dialing {clean_number}."
        }

    @classmethod
    def end_call(cls) -> Dict[str, Any]:
        """End the ongoing cellular phone call."""
        if cls.is_adb_available():
            try:
                subprocess.run(["adb", "shell", "input", "keyevent", "6"], timeout=5)
                return {"status": "ok", "message": "Call ended via ADB"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif cls.is_termux():
            try:
                subprocess.run(["input", "keyevent", "6"], timeout=5)
                return {"status": "ok", "message": "Call ended via Termux"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "ok", "message": "Call ended"}

    @classmethod
    def get_call_state(cls) -> str:
        """Return 'idle', 'ringing', or 'offhook' (active call) from Android telephony status."""
        try:
            cmd = []
            if cls.is_adb_available():
                cmd = ["adb", "shell", "dumpsys", "telephony.registry"]
            elif cls.is_termux():
                cmd = ["dumpsys", "telephony.registry"]
            
            if cmd:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                out = res.stdout
                match = re.search(r"mCallState\s*[=:]\s*(\d+)", out)
                if match:
                    val = match.group(1)
                    if val == "2":
                        return "offhook"
                    elif val == "1":
                        return "ringing"
                    elif val == "0":
                        return "idle"
                # Fallback substring checks
                if "mCallState=2" in out or "mCallState: 2" in out:
                    return "offhook"
                elif "mCallState=1" in out or "mCallState: 1" in out:
                    return "ringing"
                elif "mCallState=0" in out or "mCallState: 0" in out:
                    return "idle"
        except Exception:
            pass
        return "unknown"

