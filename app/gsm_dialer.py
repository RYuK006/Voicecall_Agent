import subprocess
import shutil
import sys
import re
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
        """Return 'active', 'dialing', 'ringing', 'idle', or 'unknown'."""
        info = cls.get_detailed_call_state()
        return info.get("state", "unknown")

    @classmethod
    def get_detailed_call_state(cls) -> Dict[str, Any]:
        """
        Query Android telecom subsystem to accurately distinguish:
        - 'idle': No active or outgoing call
        - 'dialing': Outbound call initiated, waiting for remote phone to answer
        - 'ringing': Remote phone is ringing / alerting
        - 'active': Remote party has ANSWERED the call (connected and speaking)
        - 'disconnected': Call just disconnected
        """
        try:
            # 1. Try dumpsys telecom (gold standard for ACTIVE vs DIALING)
            cmd = []
            if cls.is_adb_available():
                cmd = ["adb", "shell", "dumpsys", "telecom"]
            elif cls.is_termux():
                cmd = ["dumpsys", "telecom"]

            if cmd:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                out = res.stdout

                # Active call check (Recipient has answered)
                if re.search(r"mCalls:\s*.*\[TC@\d+,\s*ACTIVE\b", out, re.DOTALL) or re.search(r"Foreground call:\s*\[TC@\d+,\s*ACTIVE\b", out):
                    return {"state": "active", "answered": True, "source": "telecom"}

                # Dialing / Connecting check (Recipient hasn't picked up yet)
                if re.search(r"mCalls:\s*.*\[TC@\d+,\s*(DIALING|CONNECTING)\b", out, re.DOTALL) or re.search(r"Foreground call:\s*\[TC@\d+,\s*(DIALING|CONNECTING)\b", out):
                    return {"state": "dialing", "answered": False, "source": "telecom"}

                # Ringing check
                if re.search(r"mCalls:\s*.*\[TC@\d+,\s*RINGING\b", out, re.DOTALL) or re.search(r"Foreground call:\s*\[TC@\d+,\s*RINGING\b", out):
                    return {"state": "ringing", "answered": False, "source": "telecom"}

                # Disconnected / idle check
                if re.search(r"mCalls:\s*.*\[TC@\d+,\s*DISCONNECTED\b", out, re.DOTALL):
                    return {"state": "idle", "answered": False, "source": "telecom"}

                if "mCalls:\n    none" in out or "mCalls: []" in out or ("mCalls:" in out and "[TC@" not in out):
                    return {"state": "idle", "answered": False, "source": "telecom"}

            # 2. Fallback to dumpsys telephony.registry
            reg_cmd = []
            if cls.is_adb_available():
                reg_cmd = ["adb", "shell", "dumpsys", "telephony.registry"]
            elif cls.is_termux():
                reg_cmd = ["dumpsys", "telephony.registry"]

            if reg_cmd:
                res = subprocess.run(reg_cmd, capture_output=True, text=True, timeout=3)
                out = res.stdout

                # mForegroundCallState: 3 = ACTIVE, 1 = DIALING, 2 = ALERTING, 0 = IDLE
                fg_match = re.search(r"mForegroundCallState\s*[=:]\s*(\d+)", out)
                if fg_match:
                    fg_val = fg_match.group(1)
                    if fg_val == "3":
                        return {"state": "active", "answered": True, "source": "telephony.registry"}
                    elif fg_val in ("1", "2"):
                        return {"state": "dialing", "answered": False, "source": "telephony.registry"}
                    elif fg_val == "0":
                        return {"state": "idle", "answered": False, "source": "telephony.registry"}

                # Fallback mCallState
                match = re.search(r"mCallState\s*[=:]\s*(\d+)", out)
                if match:
                    val = match.group(1)
                    if val == "0":
                        return {"state": "idle", "answered": False, "source": "telephony.registry"}
                    elif val == "1":
                        return {"state": "ringing", "answered": False, "source": "telephony.registry"}
                    elif val == "2":
                        # Older Android with only aggregate offhook
                        return {"state": "active", "answered": True, "source": "telephony.registry"}
        except Exception:
            pass
        return {"state": "unknown", "answered": False, "source": "none"}

