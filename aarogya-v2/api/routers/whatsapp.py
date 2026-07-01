import os
import json
import requests
from datetime import datetime, date

import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from twilio.rest import Client as TwilioClient
from requests.auth import HTTPBasicAuth

from api.database import get_db
from api.models import HealthLog, Elder

load_dotenv()

# ─────────────────────────────────────────────
# 1. SETUP: EARS (GROQ), BRAIN (GEMINI), MOUTH (TWILIO)
# ─────────────────────────────────────────────
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    gemini_model = None

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
DISCLAIMER = "\n\n(Note: This is an automated health monitor for your personal records.)"

# ─────────────────────────────────────────────
# 2. CORE FUNCTIONS
# ─────────────────────────────────────────────
def send_whatsapp(to: str, message: str):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    from_num = "whatsapp:+14155238886"  # Ensure this is your Sandbox number
    to_num = to if "whatsapp:" in to else f"whatsapp:{to}"
    
    payload = {"From": from_num, "To": to_num, "Body": message}
    response = requests.post(url, data=payload, auth=(TWILIO_SID, TWILIO_TOKEN))
    print(f"\n--- TWILIO REPLY STATUS: {response.status_code} ---")

def extract_symptoms_ai(text: str, triggers: list, conditions: list):
    """The Intelligence Loop: Context-Aware Brain"""
    if not gemini_model: return []
    
    # Injecting patient context into the prompt
    prompt = f"""
You are a medical triage assistant. Analyze this message: "{text}"
Extract any symptoms or medical concerns mentioned. 
Return the output strictly as a JSON list of strings (e.g., ["chest pain", "breathless"]).
If no symptoms are found, return an empty list: [].
Do not include any other text.
"""
    try:
        response = gemini_model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"[ERROR] Gemini failed: {e}")
        return []

async def transcribe_audio(audio_path: str):
    print("[DEBUG] Sending audio to Groq Whisper...")
    with open(audio_path, "rb") as audio_file:
        transcript = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(audio_path, audio_file.read())
        )
    return transcript.text

# ─────────────────────────────────────────────
# 3. THE INTELLIGENCE WEBHOOK ENGINE
# ─────────────────────────────────────────────
@router.post("/incoming")
async def incoming(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    from_num = form.get("From", "").replace("whatsapp:", "")
    body = form.get("Body", "").strip()
    media_url = form.get("MediaUrl0")
    media_sid = form.get("MediaSid0")

    # 1. DATABASE LOOKUP (Identity Engine)
    elder = db.query(Elder).filter(Elder.phone == from_num).first()
    if not elder: 
        send_whatsapp(from_num, "Namaste! Aapka number register nahi hai.")
        return {"status": "not_registered"}

    # 2. AUDIO PROCESSING
    text = body.lower()
    audio_path = None 
    if media_url and "audio" in form.get("MediaContentType0", ""):
        message_id = form.get("MessageSid", "unknown_audio")
        audio_path = f"media/{message_id}.ogg"
        r = requests.get(media_url, auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN))
        with open(audio_path, "wb") as f: f.write(r.content)
        text = await transcribe_audio(audio_path)
        body = f'Transcript: "{text}"'

    # 3. CONTEXT-AWARE AI TRIAGE 
    extracted_tags = extract_symptoms_ai(text, elder.custom_triggers, elder.chronic_conditions)
    symptoms = [tag['label'] for tag in extracted_tags] if extracted_tags else []

    # 4. EMERGENCY LOGIC
    # 1. Create a safety net of default dangerous words
    base_emergencies = ["chest pain", "breathless", "bleeding", "emergency", "saans", "pain", "heart"]
    
    # 2. Safely get the patient's custom triggers (in case the array is empty)
    patient_triggers = elder.custom_triggers if elder.custom_triggers else []
    
    # 3. Combine them all into one master list
    all_triggers = base_emergencies + patient_triggers
    
    # 4. Check if the message contains ANY of the trigger words
    is_emergency = any(word.lower() in text.lower() for word in all_triggers)
    
    # 🔴 DEBUG X-RAY 🔴
    print(f"\n--- 🕵️ AI BRAIN X-RAY ---")
    print(f"1. Message received: '{text}'")
    print(f"2. Words it is looking for: {all_triggers}")
    print(f"3. Did it trigger an emergency? {is_emergency}")
    print(f"------------------------\n")
    
    # 5. DATABASE LOG
    log = HealthLog(
        elder_id=elder.id, 
        mood=2 if is_emergency else 3, 
        symptoms=symptoms, 
        notes=body,
        source="whatsapp", 
        log_date=date.today(), 
        logged_at=datetime.utcnow(),
        audio_url=audio_path
    )
    db.add(log)
    db.commit()

    # 6. REPLY & ALERT ENGINE
    if is_emergency:
        # Alert the Caregiver
        alert_msg = f"🚨 EMERGENCY ALERT: Patient {elder.name} has reported: {text}. Please contact them immediately."
        send_whatsapp(elder.caregiver_phone, alert_msg)
        
        # Reply to the Patient
        reply = "🚨 I have alerted your caregiver immediately. Please stay calm and safe."
    else:
        # Normal Reply
        reply = f"Namaste {elder.name}! Update mil gaya. Dhanyawaad! 🙏"
    
    send_whatsapp(from_num, reply + DISCLAIMER)
    return {"status": "saved"}