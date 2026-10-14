import re
import json
import httpx
from typing import Dict, Any, List, Optional, Tuple
from app.config import GROQ_API_KEY, XAI_GROK_API_KEY, GEMINI_API_KEY
from app.rsvp_manager import RSVPManager

class ConversationalAgent:
    """Conversational Voice Agent handling RSVP interactions, FAQ responses, and state updates."""

    def __init__(self, guest: Optional[Dict[str, Any]] = None, lang: str = "hi"):
        self.guest = guest or {
            "id": "GUEST-NEW",
            "name": "Guest",
            "preferred_language": "Hindi",
            "status": "Pending",
            "attendees_count": 0,
            "dietary_preference": "None",
            "notes": ""
        }
        self.lang = lang
        self.event = RSVPManager.get_event_config()
        self.history: List[Dict[str, str]] = []
        self.confirmed_status: Optional[str] = None
        self.headcount: Optional[int] = None
        self.dietary: Optional[str] = None

    def get_greeting(self) -> str:
        guest_name = self.guest.get("name", "ji")
        event_name = self.event.get("event_name", "AI India Summit 2026")
        date = self.event.get("date", "Saturday, November 14")
        
        if self.lang == "hi":
            return (
                f"Namaste {guest_name}! Main AI India Summit ki taraf se call kar rahi hoon. "
                f"Hamara event {date} ko Bengaluru mein hone ja raha hai. "
                f"Kya aap is event mein shamil ho rahe hain?"
            )
        elif self.lang == "ml":
            return (
                f"Namaskaram {guest_name}! AI India Summit-il ninnanu vilikkunnathu. "
                f"Njangalude event {date}-nu Bengaluru-vil nadakkunnu. "
                f"Ningal ee event-il pankedukkumo?"
            )
        else: # en
            return (
                f"Hello {guest_name}! I'm calling on behalf of the {event_name}. "
                f"Our flagship summit is scheduled for {date} in Bengaluru. "
                f"Will you be able to attend?"
            )

    async def generate_response(self, user_text: str) -> Tuple[str, Optional[Dict[str, Any]], bool]:
        """Process user utterance and return (agent_response_text, rsvp_update_dict, is_closing_boolean)."""
        self.history.append({"role": "user", "content": user_text})

        # Try Cloud LLM if keys are available
        response_text = None
        if XAI_GROK_API_KEY:
            response_text = await self._call_xai_grok(user_text)
        elif GROQ_API_KEY:
            response_text = await self._call_groq(user_text)
        elif GEMINI_API_KEY:
            response_text = await self._call_gemini(user_text)

        # Fallback to intelligent local rules & intent parser
        if not response_text:
            response_text = self._local_conversational_engine(user_text)

        self.history.append({"role": "assistant", "content": response_text})

        # Extract structured RSVP details and persist
        rsvp_update = self._extract_rsvp_details(user_text)
        if rsvp_update and self.guest.get("id"):
            updated = RSVPManager.update_guest_rsvp(
                guest_id=self.guest["id"],
                status=rsvp_update.get("status", self.guest.get("status", "Pending")),
                attendees_count=rsvp_update.get("attendees_count"),
                dietary_preference=rsvp_update.get("dietary_preference"),
                notes=rsvp_update.get("notes")
            )
            if updated:
                self.guest = updated

        is_closing = self.is_closing_turn(user_text, response_text)
        return response_text, rsvp_update, is_closing

    def is_closing_turn(self, user_text: str, agent_text: str) -> bool:
        """Automatically detect if this interaction marks the natural end of the call."""
        u = user_text.lower()
        a = agent_text.lower()

        user_closing = [
            "bye", "goodbye", "alvida", "rakho", "phone rakho", "cut", "kat do", "hang up", "end call",
            "shukriya", "dhanyavaad", "nandi", "thank you", "thanks", "ok bye", "chal bye", "theek hai bye",
            "chalo bye", "shubharathri", "good night", "poyi varatte", "ta ta", "disconnect", "call cut",
            "rakhta hoon", "rakh raha hoon", "rakh doon", "rakho ji", "phone rakh", "no that's all", "that's it",
            "bas itna hi", "athre ullu", "see you"
        ]
        if any(w in u for w in user_closing):
            return True

        agent_closing = [
            "shubh ho", "dhanyavaad", "have a wonderful day", "have a great day",
            "milne ke liye utsuk", "kaanaam", "look forward to seeing you",
            "goodbye", "take care", "miss karenge", "online jud sakein",
            "all details have been recorded", "sabhi details register", "ellam details record",
            "see you there", "alvida", "bye!", "have a nice day", "call disconnect", "registered successfully",
            "swagat hai"
        ]
        if any(w in a for w in agent_closing):
            return True

        return False

    def _local_conversational_engine(self, text: str) -> str:
        """Intelligent, zero-latency local fallback engine for Hindi, Malayalam, and English."""
        t = text.lower().strip()

        # 1. Check for Confirmation / Yes
        yes_keywords = [
            "haan", "ha", "bilkul", "aaunga", "aaungi", "aayenge", "yes", "yeah", "yep", "sure",
            "attending", "coming", "definite", "pankedukkum", "varum", "athe", "undu", "aah"
        ]
        no_keywords = [
            "nahi", "na", "busy", "unable", "cannot", "can't", "no", "not coming", "decline",
            "pattilla", "varilla", "illa", "varaan kazhiyilla", "sorry"
        ]
        maybe_keywords = [
            "maybe", "not sure", "dekhunga", "dekhte hain", "confuse", "later", "urappilla", "nokkam"
        ]

        # 2. Check for Specific Questions
        # Venue / Location
        if any(w in t for w in ["kahan", "venue", "location", "address", "evide", "place", "bangalore", "bengaluru"]):
            venue = self.event.get("venue", "Grand Ballroom, Tech Hub Convention Centre, Bengaluru")
            if self.lang == "hi":
                return f"Event ka venue hai: {venue}. Kya aap wahan physical aayenge ya virtual attend karenge?"
            elif self.lang == "ml":
                return f"Event venue: {venue}. Ningal direct aayi ethumo atho online aano?"
            else:
                return f"The summit is being held at {venue}. Will you be joining us in person or virtually?"

        # Time / Date
        if any(w in t for w in ["kab", "time", "date", "timing", "eppol", "tarikh", "samayam"]):
            date = self.event.get("date", "Saturday, November 14, 2026")
            time = self.event.get("time", "10:00 AM - 5:00 PM IST")
            if self.lang == "hi":
                return f"Event {date} ko subah {time} tak chalega. Kya main aapki attendance confirm kar doon?"
            elif self.lang == "ml":
                return f"Event {date}, {time}-lanu. Ningalude attendance confirm cheyyatte?"
            else:
                return f"The event is on {date}, from {time}. Shall I confirm your attendance?"

        # Parking
        if any(w in t for w in ["parking", "gadi", "car", "park"]):
            parking_info = self.event.get("faq", {}).get("parking", "Complimentary valet parking available.")
            if self.lang == "hi":
                return f"Ji haan! {parking_info} Aapko parking ki koi chinta karne ki zaroorat nahi hai. Aap akele aa rahe hain ya koi saath hai?"
            elif self.lang == "ml":
                return f"Athe, {parking_info}. Ningalude koode aarenkilum varunundo?"
            else:
                return f"Yes, {parking_info}. Will you be coming alone or bringing additional guests?"

        # Food / Dietary
        if any(w in t for w in ["food", "lunch", "khana", "meal", "veg", "non-veg", "bhojanam"]):
            food_info = self.event.get("faq", {}).get("food", "Buffet lunch with veg and non-veg options.")
            if self.lang == "hi":
                return f"Ji haan, {food_info}. Aapka preferred dietary option kya hoga - vegetarian ya non-vegetarian?"
            elif self.lang == "ml":
                return f"Athe, {food_info}. Ningalkku veg aano non-veg aano thalparyam?"
            else:
                return f"Yes, {food_info}. What is your dietary preference - Vegetarian or Non-Vegetarian?"

        # 3. Attendance Intent Handling
        if any(w in t for w in yes_keywords) and not any(w in t for w in no_keywords):
            self.confirmed_status = "Confirmed"
            # Check if headcount mentioned in same sentence
            if any(w in t for w in ["two", "2", "do", "plus one", "+1", "patni", "wife", "friend", "colleague"]):
                self.headcount = 2
            elif any(w in t for w in ["three", "3", "teen"]):
                self.headcount = 3
            else:
                self.headcount = 1

            if self.lang == "hi":
                return (
                    f"Bahut badhiya! Maine aapki attendance confirm note kar li hai. "
                    f"Aapke saath kitne log aayenge, aur aapka khana vegetarian hoga ya non-vegetarian?"
                )
            elif self.lang == "ml":
                return (
                    f"Valare santhosham! Njan attendance confirm cheythu. "
                    f"Ningalude koode ethra aalukal varum? Dietary preference veg aano non-veg aano?"
                )
            else:
                return (
                    f"Wonderful! I have marked your attendance as Confirmed. "
                    f"How many guests will be joining with you, and do you have any dietary preferences?"
                )

        if any(w in t for w in no_keywords):
            self.confirmed_status = "Declined"
            if self.lang == "hi":
                return "Koi baat nahi, hum aapko miss karenge! Hum aapko virtual streaming link bhej denge taaki aap online jud sakein. Shukriya!"
            elif self.lang == "ml":
                return "Saramilla! Njangal online streaming link ayachu tharaam. Samayam thannathinu nandi!"
            else:
                return "No problem at all! We'll miss you in person, but we will send you the virtual stream link so you can tune in online. Thank you!"

        if any(w in t for w in maybe_keywords):
            self.confirmed_status = "Pending"
            if self.lang == "hi":
                return "Samajh gaya! Maine aapka status tentative mark kiya hai. Event se 2 din pehle hum ek baar reminder bhej denge. Dhanyavaad!"
            elif self.lang == "ml":
                return "Manassilai! Njangal status tentative aayi mark cheyyunnu. Event-inu munp reminder ayakkum. Nandi!"
            else:
                return "Understood! I'll keep your status tentative and we will send a friendly reminder closer to the date. Thank you!"

        # Headcount & Food response follow-up
        if any(w in t for w in ["veg", "vegetarian", "non-veg", "jain", "vegan", "alone", "akele", "2", "two", "do", "1", "one", "ek"]):
            if "veg" in t and "non" not in t:
                self.dietary = "Vegetarian"
            elif "non" in t:
                self.dietary = "Non-Vegetarian"
            
            if self.lang == "hi":
                return "Perfect! Sabhi details register ho gayi hain. Hum aapse 14 November ko AI India Summit mein milne ke liye utsuk hain. Aapka din shubh ho!"
            elif self.lang == "ml":
                return "Nannayi! Ellam details record cheythu. November 14-nu kaanaam. Have a wonderful day!"
            else:
                return "All details have been recorded successfully. We look forward to seeing you at the AI India Summit on November 14th. Have a great day!"

        # Goodbye / Thank you handling
        goodbye_words = ["bye", "goodbye", "alvida", "rakhta hu", "rakh do", "cut", "shukriya", "dhanyavaad", "nandi", "thank you", "thanks", "ok bye"]
        if any(w in t for w in goodbye_words):
            if self.lang == "hi":
                return "Shukriya! AI India Summit mein aapka swagat hai. Alvida, aapka din shubh ho!"
            elif self.lang == "ml":
                return "Nandi! Event-il kaanaam. Have a wonderful day ahead!"
            else:
                return "Thank you so much! We look forward to seeing you at the summit. Have a great day!"

        # Default polite clarification
        if self.lang == "hi":
            return "Ji, kya aap is event mein shamil ho rahe hain? Aap attendance ya agenda ke baare mein kuch bhi pooch sakte hain."
        elif self.lang == "ml":
            return "Ningal ee event-il pankedukkumo? Eventine kurichu enthenkilum chodikkunnundo?"
        else:
            return "Will you be attending the summit? Feel free to let me know or ask any questions regarding the venue and agenda."

    def _extract_rsvp_details(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract structured RSVP state updates from user utterances."""
        t = text.lower()
        update: Dict[str, Any] = {}

        if any(w in t for w in ["haan", "ha", "bilkul", "aaunga", "aaungi", "yes", "yeah", "attending", "coming", "varum", "athe"]):
            update["status"] = "Confirmed"
            update["attendees_count"] = 1
        elif any(w in t for w in ["nahi", "na", "busy", "unable", "cannot", "can't", "no", "varilla", "pattilla"]):
            update["status"] = "Declined"
            update["attendees_count"] = 0

        # Numbers
        if re.search(r"\b(2|two|do|rendu)\b", t):
            update["attendees_count"] = 2
        elif re.search(r"\b(3|three|teen|moonnu)\b", t):
            update["attendees_count"] = 3
        elif re.search(r"\b(1|one|ek|onnu|alone|myself|single)\b", t):
            update["attendees_count"] = 1

        # Dietary
        if "non-veg" in t or "non veg" in t:
            update["dietary_preference"] = "Non-Vegetarian"
        elif "veg" in t or "vegetarian" in t:
            update["dietary_preference"] = "Vegetarian"
        elif "vegan" in t:
            update["dietary_preference"] = "Vegan"

        return update if update else None

    async def _call_xai_grok(self, user_text: str) -> Optional[str]:
        """Optional xAI Grok (grok-2 / grok-beta) real-time inference."""
        try:
            url = "https://api.x.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {XAI_GROK_API_KEY}",
                "Content-Type": "application/json"
            }
            system_prompt = (
                f"You are Priya, a friendly, concise AI calling agent representing {self.event.get('event_name')}. "
                f"You are speaking in {self.lang} with natural, polite code-mixing. Keep your spoken responses concise (1-2 short sentences max). "
                f"Event Details: {json.dumps(self.event)}. Current Guest: {self.guest.get('name')}. "
                f"IMPORTANT: Once the guest confirms or declines attendance and provides headcount/dietary details, OR if they say goodbye/thank you, wrap up the call politely with a warm farewell (e.g. 'Thank you, we look forward to seeing you at the summit! Have a wonderful day, goodbye!' or 'Shukriya, alvida!'). This allows the system to automatically conclude the call."
            )
            messages = [{"role": "system", "content": system_prompt}] + self.history
            payload = {
                "model": "grok-beta",
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 120
            }
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"xAI Grok API call error: {e}")
        return None

    async def _call_groq(self, user_text: str) -> Optional[str]:
        """Optional Cloud Groq Llama-3 sub-second inference."""
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            system_prompt = (
                f"You are Priya, a friendly AI calling agent representing {self.event.get('event_name')}. "
                f"You are speaking in {self.lang} with natural code-mixing. Keep your spoken responses concise (1-2 short sentences max). "
                f"Event Details: {json.dumps(self.event)}. Current Guest: {self.guest.get('name')}. "
                f"IMPORTANT: Once the guest confirms or declines attendance and provides headcount/dietary details, OR if they say goodbye/thank you, wrap up the call politely with a warm farewell (e.g. 'Thank you, we look forward to seeing you at the summit! Have a wonderful day, goodbye!' or 'Shukriya, alvida!'). This allows the system to automatically conclude the call."
            )
            messages = [{"role": "system", "content": system_prompt}] + self.history
            candidate_models = ["qwen/qwen3.8-27b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
            for model_name in candidate_models:
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 120
                }
                async with httpx.AsyncClient(timeout=4.0) as client:
                    res = await client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        if content:
                            return content
        except Exception as e:
            print(f"Groq API call fallback: {e}")
        return None

    async def _call_gemini(self, user_text: str) -> Optional[str]:
        """Optional Cloud Google Gemini Flash inference."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = (
                f"You are Priya, a friendly AI voice calling agent for {self.event.get('event_name')}. "
                f"Respond in {self.lang} conversationally and concisely (1-2 spoken sentences). "
                f"If the guest confirms or declines and gives headcount, conclude warmly with a goodbye/thank you. "
                f"User said: {user_text}"
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Gemini API call fallback: {e}")
        return None
