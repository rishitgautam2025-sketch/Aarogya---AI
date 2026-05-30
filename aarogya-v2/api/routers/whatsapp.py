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
# The Brain (Gemini)
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    gemini_model = None

# The Ears (Groq)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# The Mouth (Twilio)
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
DISCLAIMER = "\n\n(Note: This is a summary of your daily symptom log for your personal records.)"

# ─────────────────────────────────────────────
# 2. CORE FUNCTIONS
# ─────────────────────────────────────────────
def send_whatsapp(to: str, message: str):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    from_num = TWILIO_NUMBER if "whatsapp:" in TWILIO_NUMBER else f"whatsapp:{TWILIO_NUMBER}"
    to_num = to if "whatsapp:" in to else f"whatsapp:{to}"
    
    payload = {"From": from_num, "To": to_num, "Body": message}
    response = requests.post(url, data=payload, auth=(TWILIO_SID, TWILIO_TOKEN))
    print(f"\n--- TWILIO REPLY STATUS: {response.status_code} ---")

def extract_symptoms_ai(text: str):
    """The Gemini Phase 2 Brain"""
    if not gemini_model: return []
    prompt = f"""Extract symptoms from: "{text}". Categorize as NEW SYMPTOM, REPEATED, or WORSENING. Return ONLY a raw JSON array of objects with 'type' and 'label' keys. Do not use markdown."""
    try:
        response = gemini_model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"[ERROR] Gemini failed: {e}")
        return []

async def transcribe_audio(audio_path: str):
    """The Groq Phase 1 Ears"""
    print("[DEBUG] Sending audio to Groq Whisper...")
    with open(audio_path, "rb") as audio_file:
        transcript = groq_client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(audio_path, audio_file.read())
        )
    return transcript.text

# ─────────────────────────────────────────────
# 3. THE WEBHOOK ENGINE
# ─────────────────────────────────────────────
@router.post("/incoming")
async def incoming(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    from_num = form.get("From", "").replace("whatsapp:", "")
    body = form.get("Body", "").strip()
    media_url = form.get("MediaUrl0")
    media_sid = form.get("MediaSid0")

    # 1. PRIVACY CLEANUP 
    if media_sid:
        try: twilio_client.api.v2010.account(TWILIO_SID).media(media_sid).delete()
        except Exception: pass

    if not body and not media_url: 
        return {"status": "ignored"}

    # 2. AUDIO PROCESSING & FIX
    text = body.lower()
    audio_path = None  # <--- THE CRITICAL FIX IS RIGHT HERE!
    
    if media_url and "audio" in form.get("MediaContentType0", ""):
        message_id = form.get("MessageSid", "unknown_audio")
        audio_path = f"media/{message_id}.ogg"
        
        # Download Audio
        r = requests.get(media_url, auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN))
        with open(audio_path, "wb") as f: 
            f.write(r.content)

        # Groq Transcription
        text = await transcribe_audio(audio_path)
        body = f'Transcript: "{text}"'

    # 3. GEMINI AI TRIAGE 
    extracted_tags = extract_symptoms_ai(text)
    symptoms = [tag['label'] for tag in extracted_tags] if extracted_tags else []

    # 4. SAFETY SHIELD & EMERGENCY CHECK
    emergency_keywords = ["chest pain", "saans", "breathless", "bleeding", "emergency", "heart"]
    is_emergency = any(word in text.lower() for word in emergency_keywords)

    # 5. MOOD CALCULATION
    mood = 3 # Default: Neutral
    if extracted_tags:
        if any(tag['type'] == 'WORSENING' for tag in extracted_tags) or is_emergency:
            mood = 1  # Critical
        elif any(tag['type'] == 'NEW SYMPTOM' for tag in extracted_tags):
            mood = 2  # Sick
    elif "theek" in text or "acha" in text:
        mood = 4  # Stable

    # 6. DATABASE LOGIC
    elder = db.query(Elder).filter(Elder.phone == from_num).first()
    if not elder: 
        send_whatsapp(from_num, "Namaste! Aapka number register nahi hai.")
        return {"status": "not_registered"}
    
    log = HealthLog(
        elder_id=elder.id, 
        mood=mood, 
        symptoms=symptoms, 
        notes=body,
        source="whatsapp", 
        log_date=date.today(), 
        logged_at=datetime.utcnow(),
        audio_url=audio_path  # Variable is now guaranteed to exist!
    )
    db.add(log)
    db.commit()
    print(f"✅ SUCCESSFULLY SAVED TO DATABASE: {elder.name}")

    # 7. MULTILINGUAL REPLY ENGINE
    if is_emergency:
        reply = "🚨 EMERGENCY ALERT: Please call for help immediately."
    elif elder.preferred_language == "spanish":
        if mood >= 4: reply = f"¡Hola {elder.name}! Qué bueno escuchar que te sientes bien. 🙏"
        elif mood <= 2: reply = f"¡Hola {elder.name}! He notado que tienes {', '.join(symptoms)}. Descansa. 🏥"
        else: reply = f"¡Hola {elder.name}! Actualización recibida. ¡Gracias! 🙏"
    elif elder.preferred_language == "english":
        if mood >= 4: reply = f"Hello {elder.name}! It's great to hear you are feeling well. 🙏"
        elif mood <= 2: reply = f"Hello {elder.name}! I noted your symptoms: {', '.join(symptoms)}. Please rest. 🏥"
        else: reply = f"Hello {elder.name}! Update received. Thank you! 🙏"
    else:
        # Default Hinglish
        if mood >= 4: reply = f"Namaste {elder.name}! Aap theek hain, yeh sunke acha laga. 🙏"
        elif mood <= 2: reply = f"Namaste {elder.name}! Aapne bataya ki {', '.join(symptoms)}. Main note kar liya. Aram karein. 🏥"
        else: reply = f"Namaste {elder.name}! Update mil gaya. Dhanyawaad! 🙏"
    
    send_whatsapp(from_num, reply + DISCLAIMER)
    return {"status": "saved"}