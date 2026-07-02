import os
import json
import requests
import uuid
from datetime import datetime, date, timezone

from groq import Groq
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from twilio.rest import Client as TwilioClient
from requests.auth import HTTPBasicAuth

# Architecture Imports
from api.config import s3_client, AWS_BUCKET_NAME, supabase, gemini_model
from api.database import SessionLocal, get_db
import api.models
from api.notifications import trigger_emergency_call
from api.utils import send_emergency_alert

load_dotenv()

# SETUP: API Clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

def send_whatsapp(to: str, message: str):
    if not TWILIO_SID or not TWILIO_TOKEN: return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    to_num = to if "whatsapp:" in to else f"whatsapp:{to}"
    payload = {"From": TWILIO_NUMBER, "To": to_num, "Body": message}
    try:
        requests.post(url, data=payload, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=10)
    except Exception as e:
        print(f"[ERROR] Twilio API: {e}")

def heavy_audio_processing_pipeline(data: dict):
    print("DEBUG: Pipeline just started!")
    db = SessionLocal() 
    try:
        from_num = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "").strip()
        media_url_0 = data.get("MediaUrl0") 
        media_content_type = data.get("MediaContentType0", "")
        
        elder = db.query(api.models.Elder).filter(api.models.Elder.phone == from_num).first()
        if not elder:
            send_whatsapp(from_num, "Namaste! Aapka number register nahi hai.")
            return

        text_to_process = body.lower()
        s3_file_url = None
        vision_part = None 

        # --- A. HANDLE MEDIA ---
        if media_url_0:
            media_response = requests.get(media_url_0, auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID else None)
            
            if media_response.status_code in [200, 201]:
                media_bytes = media_response.content
                
                # Image Routing
                if media_content_type.startswith("image/"):
                    file_extension = media_content_type.split("/")[-1]
                    file_name = f"{elder.id}_img_{uuid.uuid4().hex}.{file_extension}"
                    vision_part = {"mime_type": media_content_type, "data": media_bytes}
                    if not text_to_process:
                        text_to_process = "User sent a photo for medical evaluation."
                        
                # Audio Routing (Groq Whisper)
                else: 
                    file_name = f"{elder.id}_audio_{uuid.uuid4().hex}.ogg"
                    try:
                        transcript = groq_client.audio.translations.create(
                            model="whisper-large-v3",
                            file=("voice_note.ogg", media_bytes)
                        )
                        text_to_process = transcript.text
                    except Exception as e:
                        print(f"[ERROR] Groq Failed: {e}")
                        text_to_process = "Audio transcription failed."
                
                # S3 Upload
                if s3_client:
                    s3_client.put_object(
                        Bucket=AWS_BUCKET_NAME,
                        Key=file_name,
                        Body=media_bytes,
                        ContentType=media_content_type or "application/octet-stream"
                    )
                    s3_file_url = f"https://{AWS_BUCKET_NAME}.s3.ap-south-1.amazonaws.com/{file_name}"

        # --- B. AI INTELLIGENCE ---
        symptoms = []
        is_emergency = False
        
        if supabase and gemini_model:
            try:
                # 1. Save Raw Log
                log_res = supabase.table("voice_logs").insert({
                    "patient_id": str(elder.id), 
                    "raw_text": text_to_process,
                    "audio_url": s3_file_url, 
                    "processed": True
                }).execute()
                log_id = log_res.data[0]['id']

                # 2. Context-Aware Prompt
                patient_conditions = elder.chronic_conditions if elder.chronic_conditions else []
                custom_triggers = elder.custom_triggers if elder.custom_triggers else []
                universal_red_flags = ["chest pain", "shortness of breath", "severe breathing difficulty", "unconscious", "heavy bleeding", "sudden numbness", "choking", "fainting"]
                
                prompt = f"""You are a medical triage AI routing notifications for a caretaker.
                Patient Profile:
                - Chronic Conditions: {', '.join(patient_conditions) if patient_conditions else 'None reported'}
                - Custom Alert Triggers: {', '.join(custom_triggers) if custom_triggers else 'None set'}
                Universal Red Flags: {', '.join(universal_red_flags)}
                
                Transcript/Context: "{text_to_process}"
                
                Task: Extract reported symptoms. Evaluate urgency. Set "is_emergency" to true ONLY IF an extracted symptom directly matches or worsens a risk related to the Universal Red Flags OR the Custom Alert Triggers.
                Return ONLY a raw JSON array of objects with keys: 'type', 'label', and 'is_emergency' (boolean). Do not use markdown."""
                
                # 3. Gemini Generation
                response = gemini_model.generate_content([prompt, vision_part]) if vision_part else gemini_model.generate_content(prompt)
                
                # 4. JSON Parse & Emergency Telephony Routing
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                if not clean_text.startswith('['): clean_text = f"[{clean_text}]"
                symptoms = json.loads(clean_text)
                
                for item in symptoms:
                    if item.get("is_emergency") is True:
                        is_emergency = True
                        current_time = datetime.now(timezone.utc)
                        last_alert = elder.last_alert_sent
                        
                        if last_alert:
                            if last_alert.tzinfo is None:
                                last_alert = last_alert.replace(tzinfo=timezone.utc)
                            if (current_time - last_alert).total_seconds() < 900:
                                print("[INFO] Emergency call suppressed (15 min cooldown).")
                                break
                        
                        # Trigger Call
                        if elder.caregiver_phone:
                            trigger_emergency_call(elder.caregiver_phone, elder.name, item.get('label', 'Emergency'), item.get('reasoning', 'Condition met.'))
                            supabase.table("elders").update({"last_alert_sent": current_time.isoformat()}).eq("id", elder.id).execute()
                        break
                        
            except Exception as e:
                print(f"[ERROR] AI Logic Failed: {e}")

        # --- C. EMAIL ALERTS & DATABASE LOGGING ---
        if is_emergency:
            send_emergency_alert(patient_name=elder.name, symptom="Critical AI Flag", raw_message=text_to_process)

        if symptoms and 'log_id' in locals():
            tags = [{"log_id": log_id, "patient_id": str(elder.id), "tag_type": t.get("type", "NEW SYMPTOM"), "label": t.get("label", "General Symptom")} for t in symptoms]
            supabase.table("symptom_tags").insert(tags).execute()
        
        # Save to primary SQLAlchemy HealthLog
        log = api.models.HealthLog(
            elder_id=elder.id, 
            mood=2 if is_emergency else 3, 
            symptoms=[tag.get('label') for tag in symptoms] if symptoms else [], 
            notes=text_to_process,
            source="whatsapp", 
            log_date=date.today(), 
            logged_at=datetime.utcnow(),
            audio_url=s3_file_url
        )
        db.add(log)
        db.commit()

        # --- D. PATIENT REPLY ---
        reply = f"Namaste {elder.name}! Aapka message save ho gaya hai. Aapke caretaker ise jald hi sun lenge. 🙏"
        send_whatsapp(from_num, reply)

    except Exception as e:
        print(f"[CRITICAL BACKGROUND ERROR] {e}")
    finally:
        db.close()

@router.post("/incoming")
async def incoming(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    data = {k: v for k, v in form_data.items()}
    background_tasks.add_task(heavy_audio_processing_pipeline, data)
    return {"status": "accepted"}