import json
import csv
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.config import EVENT_CONFIG_PATH, GUESTS_FILE_PATH, RSVP_CSV_PATH

class RSVPManager:
    """Manages Event configuration, Guest lists, and RSVP state synchronization."""
    _lock = threading.Lock()

    @classmethod
    def get_event_config(cls) -> Dict[str, Any]:
        with cls._lock:
            if EVENT_CONFIG_PATH.exists():
                try:
                    with open(EVENT_CONFIG_PATH, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return {
                "event_name": "AI India Summit 2026",
                "organizer": "Sarvam AI & IndicTech Community",
                "date": "Saturday, November 14, 2026",
                "time": "10:00 AM - 5:00 PM IST",
                "venue": "Grand Ballroom, Tech Hub Convention Centre, Bengaluru",
                "virtual_link": "https://summit.ai-india.org/live",
                "description": "Annual flagship conference on Indic AI, Voice Agents, and Sovereign Foundation Models.",
                "agenda": [],
                "faq": {}
            }

    @classmethod
    def save_event_config(cls, config: Dict[str, Any]) -> bool:
        with cls._lock:
            try:
                with open(EVENT_CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"Error saving event config: {e}")
                return False

    @classmethod
    def get_guests(cls) -> List[Dict[str, Any]]:
        with cls._lock:
            if GUESTS_FILE_PATH.exists():
                try:
                    with open(GUESTS_FILE_PATH, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return []

    @classmethod
    def save_guests(cls, guests: List[Dict[str, Any]]) -> bool:
        with cls._lock:
            try:
                with open(GUESTS_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(guests, f, indent=2, ensure_ascii=False)
                cls._export_to_csv_unlocked(guests)
                return True
            except Exception as e:
                print(f"Error saving guests: {e}")
                return False

    @classmethod
    def find_guest(cls, identifier: str) -> Optional[Dict[str, Any]]:
        """Find guest by ID, name substring, or phone number."""
        guests = cls.get_guests()
        ident_lower = identifier.strip().lower()
        
        for g in guests:
            if g.get("id", "").lower() == ident_lower:
                return g
            if ident_lower in g.get("name", "").lower():
                return g
            clean_phone = "".join(filter(str.isdigit, g.get("phone", "")))
            clean_ident = "".join(filter(str.isdigit, identifier))
            if clean_ident and (clean_ident in clean_phone or clean_phone in clean_ident):
                return g
        return None

    @classmethod
    def update_guest_rsvp(
        cls,
        guest_id: str,
        status: str,
        attendees_count: Optional[int] = None,
        dietary_preference: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        with cls._lock:
            guests = []
            if GUESTS_FILE_PATH.exists():
                try:
                    with open(GUESTS_FILE_PATH, "r", encoding="utf-8") as f:
                        guests = json.load(f)
                except Exception:
                    guests = []

            updated_guest = None
            for g in guests:
                if g.get("id") == guest_id:
                    g["status"] = status
                    if attendees_count is not None:
                        g["attendees_count"] = max(1, int(attendees_count))
                    elif status == "Confirmed" and g.get("attendees_count", 0) == 0:
                        g["attendees_count"] = 1
                    elif status == "Declined":
                        g["attendees_count"] = 0

                    if dietary_preference:
                        g["dietary_preference"] = dietary_preference
                    if notes:
                        g["notes"] = notes
                    
                    g["last_call_at"] = datetime.now(timezone.utc).isoformat()
                    updated_guest = g
                    break

            if updated_guest:
                with open(GUESTS_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(guests, f, indent=2, ensure_ascii=False)
                cls._export_to_csv_unlocked(guests)

            return updated_guest

    @classmethod
    def add_guest(cls, guest: Dict[str, Any]) -> Dict[str, Any]:
        with cls._lock:
            guests = []
            if GUESTS_FILE_PATH.exists():
                try:
                    with open(GUESTS_FILE_PATH, "r", encoding="utf-8") as f:
                        guests = json.load(f)
                except Exception:
                    pass
            
            if not guest.get("id"):
                guest["id"] = f"GST-{len(guests) + 101}"
            
            if not guest.get("status"):
                guest["status"] = "Pending"
            
            guests.append(guest)
            with open(GUESTS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(guests, f, indent=2, ensure_ascii=False)
            cls._export_to_csv_unlocked(guests)
            return guest

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        guests = cls.get_guests()
        total = len(guests)
        confirmed = sum(1 for g in guests if g.get("status") == "Confirmed")
        declined = sum(1 for g in guests if g.get("status") == "Declined")
        pending = sum(1 for g in guests if g.get("status") == "Pending")
        headcount = sum(g.get("attendees_count", 0) for g in guests if g.get("status") == "Confirmed")
        
        return {
            "total_guests": total,
            "confirmed": confirmed,
            "declined": declined,
            "pending": pending,
            "total_attendees_headcount": headcount
        }

    @classmethod
    def _export_to_csv_unlocked(cls, guests: List[Dict[str, Any]]):
        """Export guest list to CSV for Google Sheets / Make.com integration."""
        try:
            fields = ["id", "name", "phone", "preferred_language", "status", "attendees_count", "dietary_preference", "notes", "last_call_at"]
            with open(RSVP_CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for g in guests:
                    row = {k: g.get(k, "") for k in fields}
                    writer.writerow(row)
        except Exception as e:
            print(f"Error exporting CSV: {e}")
