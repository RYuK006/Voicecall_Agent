import subprocess
import shutil
import sys
import re
import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any

CURRENT_BRIDGE_URL = os.getenv("TERMUX_BRIDGE_URL", "")

class GSMDialer:
    """Manages cellular SIM dialing via Termux Wi-Fi Bridge, Android ADB, or native Termux."""

    @classmethod
    def set_termux_bridge_url(cls, url: str) -> str:
        """Dynamically configure and sanitize the phone's Termux Wi-Fi bridge IP address."""
        global CURRENT_BRIDGE_URL
        url = url.strip()
        if not url:
            CURRENT_BRIDGE_URL = ""
            return ""

        # Normalize malformed scheme like 'http: /', 'http:/', 'http: //', etc.
        url = re.sub(r"^http:\s*/*", "http://", url, flags=re.IGNORECASE)
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"

        # Fix common typo where user types dot instead of colon for port (e.g. 192.168.1.7.8080 -> 192.168.1.7:8080)
        url = re.sub(r"(\d+\.\d+\.\d+\.\d+)\.(\d+)$", r"\1:\2", url)

        # Remove trailing slashes
        url = url.rstrip("/")

        # If no port is specified on an IPv4 address, default to :8080
        if re.search(r"http://\d+\.\d+\.\d+\.\d+$", url):
            url = f"{url}:8080"

        CURRENT_BRIDGE_URL = url
        return CURRENT_BRIDGE_URL

    @classmethod
    def test_termux_bridge(cls, url: Optional[str] = None) -> Dict[str, Any]:
        """Ping the Termux bridge to test reachability."""
        bridge = url or cls.get_termux_bridge_url()
        if not bridge:
            return {"status": "error", "message": "No bridge URL configured"}
        try:
            req = urllib.request.Request(f"{bridge}/ping", headers={"User-Agent": "VoicecallAgent/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return {"status": "connected", "bridge_url": bridge}
        except Exception as e:
            return {"status": "error", "message": str(e), "bridge_url": bridge}
        return {"status": "error", "message": "Failed to connect", "bridge_url": bridge}

    @classmethod
    def get_termux_bridge_url(cls) -> str:
        """Get currently configured Termux Wi-Fi bridge URL."""
        global CURRENT_BRIDGE_URL
        if not CURRENT_BRIDGE_URL:
            raw = os.getenv("TERMUX_BRIDGE_URL", "").strip()
            if raw:
                cls.set_termux_bridge_url(raw)
        return CURRENT_BRIDGE_URL

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

        # 1. Over Termux Wi-Fi Bridge (Zero USB cable, phone anywhere on Wi-Fi):
        bridge = cls.get_termux_bridge_url()
        if bridge:
            try:
                data = json.dumps({"phone": clean_number}).encode("utf-8")
                req = urllib.request.Request(
                    f"{bridge}/dial",
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    return json.loads(response.read().decode())
            except Exception as e:
                return {"status": "error", "message": f"Termux Bridge ({bridge}) dial error: {e}"}

        # 2. If running standalone on Android inside Termux:
        if cls.is_termux():
            try:
                cmd = ["termux-telephony-call", clean_number]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    return {"status": "ok", "mode": "termux", "message": f"Dialing {clean_number} via Termux SIM"}
                return {"status": "error", "message": res.stderr}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # 3. If running on PC connected to Android phone via ADB:
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

        # 4. Windows Phone Link / System Tel Protocol Handler:
        if sys.platform == "win32":
            try:
                os.startfile(f"tel:{clean_number}")
                return {
                    "status": "ok",
                    "mode": "phone_link",
                    "message": f"Dialing {clean_number} via Windows Phone Link"
                }
            except Exception:
                pass

        return {
            "status": "simulated",
            "message": f"Neither Termux Bridge nor ADB detected. Please run 'python termux_bridge.py' on phone or connect Windows Phone Link."
        }

    @classmethod
    def end_call(cls) -> Dict[str, Any]:
        """End the ongoing cellular phone call."""
        bridge = cls.get_termux_bridge_url()
        if bridge:
            try:
                req = urllib.request.Request(
                    f"{bridge}/hangup",
                    data=b"{}",
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    return json.loads(response.read().decode())
            except Exception:
                pass

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
            # 0. Check Termux Wi-Fi Bridge first
            bridge = cls.get_termux_bridge_url()
            if bridge:
                try:
                    req = urllib.request.Request(f"{bridge}/status")
                    with urllib.request.urlopen(req, timeout=2) as response:
                        res_body = json.loads(response.read().decode())
                        res_body["source"] = "termux-bridge"
                        return res_body
                except Exception:
                    pass

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

    @classmethod
    def get_bluetooth_status(cls) -> Dict[str, Any]:
        """Detect connected Bluetooth Hands-Free phones on Windows or Termux."""
        has_gateway = False
        phones = []

        if sys.platform == "win32":
            try:
                cmd = [
                    "powershell", "-NoProfile", "-Command",
                    "(Get-PnpDevice -Class Bluetooth | Where-Object Present).FriendlyName"
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
                if res.returncode == 0:
                    lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
                    has_gateway = any("headset" in l.lower() for l in lines)
                    phones = list(set([
                        l for l in lines 
                        if not any(k in l.lower() for k in [
                            "bluetooth", "adapter", "enumerator", "generic", 
                            "transport", "protocol", "nap", "pse", "gateway", 
                            "service", "attribute"
                        ])
                    ]))
            except Exception:
                pass

        elif cls.is_termux():
            try:
                res = subprocess.run(["dumpsys", "bluetooth_manager"], capture_output=True, text=True, timeout=3)
                if "state: ON" in res.stdout:
                    has_gateway = True
            except Exception:
                pass

        has_vb_cable = False
        if sys.platform == "win32":
            try:
                cmd_vb = [
                    "powershell", "-NoProfile", "-Command",
                    "(Get-PnpDevice | Where-Object { $_.FriendlyName -like '*VB-Audio*' -and $_.Present }).FriendlyName"
                ]
                res_vb = subprocess.run(cmd_vb, capture_output=True, text=True, timeout=3)
                if "VB-Audio" in res_vb.stdout:
                    has_vb_cable = True
            except Exception:
                pass

        phone_name = phones[0] if phones else "None"
        is_ready = bool(has_gateway or phone_name != "None" or has_vb_cable)
        badge_text = "VB-CABLE Ready" if has_vb_cable else f"{phone_name} Ready"
        return {
            "has_handsfree_gateway": has_gateway,
            "has_vb_cable": has_vb_cable,
            "connected_phone": phone_name,
            "all_phones": phones,
            "status": "connected" if is_ready else "not_connected",
            "message": badge_text
        }


