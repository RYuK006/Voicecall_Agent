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
                subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_ENDCALL"], timeout=5)
                return {"status": "ok", "message": "Call ended via ADB"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "ok", "message": "Call ended"}
