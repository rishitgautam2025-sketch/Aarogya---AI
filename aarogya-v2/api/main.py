"""
Aarogya AI V2 — FastAPI REST API

Endpoints:
  GET  /health          — uptime check
  GET  /symptoms        — list all valid symptom names
  GET  /diseases        — list all diseases the model knows
  POST /predict         — disease prediction (top 3 with confidence)
  POST /predict/injury  — injury triage using Ottawa / Pittsburgh rules
  POST /feedback        — log prediction feedback for retraining
  POST /whatsapp/incoming — receive WhatsApp messages from parents

Run: uvicorn api.main:app --reload --port 8000
"""

from urllib import response

from dotenv import load_dotenv
load_dotenv()

import json
import os
import traceback
import uuid
import io
import joblib
import numpy as np
import requests
import boto3
import smtplib
from email.message import EmailMessage

from groq import Groq
from requests.auth import HTTPBasicAuth
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

# --- NEW PHASE 2 IMPORTS ---
from supabase import create_client, Client
import google.generativeai as genai

# Local imports
from api.scheduler import start_scheduler
from api.database import Base, engine, get_db, SessionLocal
import api.models
from api.routers.auth import router as auth_router
from api.routers.elder_monitor import router as elder_monitor_router

def send_emergency_alert(patient_name, symptom, raw_message):
    SENDER_EMAIL = "aarogya.ai.alerts@gmail.com" 
    APP_PASSWORD = os.getenv("EMAIL_PASS")
    RECEIVER_EMAIL = "rishitgautam8@gmail.com"

    msg = EmailMessage()
    msg.set_content(f"""
    CRITICAL HEALTH ALERT
    Patient: {patient_name}
    Flagged Symptom: {symptom}
    Original Transcript: "{raw_message}"
    """)

    msg['Subject'] = f"URGENT: Aarogya AI Alert - {patient_name}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print("Emergency email sent successfully!")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

# ─────────────────────────────────────────────
# NEW PHASE 2: SUPABASE & GEMINI INITIALIZATION
# ─────────────────────────────────────────────
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
    print("[INFO] Supabase Vault connected successfully.")
else:
    supabase = None

google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    print("[INFO] Gemini AI Brain online.")
else:
    gemini_model = None

def send_emergency_alert(patient_name, symptom, raw_message):
    # Your credentials (store these securely in Render environment variables later)
    SENDER_EMAIL = "aarogya.ai.alerts@gmail.com" 
    APP_PASSWORD = os.getenv("EMAIL_PASS")
    RECEIVER_EMAIL = "rishitgautam8@gmail.com" # Where you want to receive the alert

    msg = EmailMessage()
    msg.set_content(f"""
    CRITICAL HEALTH ALERT
    
    Patient: {patient_name}
    Flagged Symptom: {symptom}
    
    Original Message / Transcript: 
    "{raw_message}"
    
    Action Required: Please contact them immediately. This is an automated Aarogya AI alert.
    """)

    msg['Subject'] = f"URGENT: Aarogya AI Alert - {patient_name}"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Emergency email sent for {symptom}!")
    except Exception as e:
        print(f"Failed to send email alert: {e}")
        
# ─────────────────────────────────────────────
# APP SETUP & MIDDLEWARE (Cleaned & Unified)
# ─────────────────────────────────────────────
api.models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Aarogya AI V2",
    description="Health intelligence API — symptom triage, injury assessment, and remote elder care",
    version="2.0.0",
)

# 1. Create a "media" folder if it doesn't exist
os.makedirs("media", exist_ok=True)

# 2. Tell FastAPI to make this folder publicly accessible
app.mount("/media", StaticFiles(directory="media"), name="media")

# 3. Add CORS Middleware so React can access the API and the media files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    start_scheduler()

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "CRASH_MESSAGE": str(exc),
            "EXACT_LOCATION": traceback.format_exc().splitlines()[-3:]
        }
    )

# Include routers
app.include_router(auth_router)
app.include_router(elder_monitor_router)

# ─────────────────────────────────────────────
# LOAD MODEL ARTIFACTS
# ─────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent.parent / "model"

try:
    model = joblib.load(MODEL_DIR / "best_model.pkl")
    le = joblib.load(MODEL_DIR / "label_encoder.pkl")
    with open(MODEL_DIR / "symptoms.json") as f:
        SYMPTOM_COLS = json.load(f)
    with open(MODEL_DIR / "model_report.json") as f:
        MODEL_REPORT = json.load(f)
    MODEL_LOADED = True
except FileNotFoundError:
    MODEL_LOADED = False
    SYMPTOM_COLS = []
    MODEL_REPORT = {}
    print("[WARN] Model not found. Run model/train.py first. /predict will return 503.")

SYMPTOM_SET = set(SYMPTOM_COLS)

# ─────────────────────────────────────────────
# SPRINT 1: SECURE ASYNC WHATSAPP WEBHOOK & TRACKER
# ─────────────────────────────────────────────
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# 1. AWS S3 CONFIGURATION (Mumbai Region for Data Compliance)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "aarogya-voice-logs")

# FIX: Only initialize boto3 if keys are present to prevent startup crash
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name="ap-south-1" 
    )
else:
    s3_client = None

def send_whatsapp(to: str, message: str):
    if not TWILIO_SID or not TWILIO_TOKEN:
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    payload = {"From": TWILIO_NUMBER, "To": f"whatsapp:{to}", "Body": message}
    try:
        requests.post(url, data=payload, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=10)
    except Exception as e:
        print(f"[ERROR] Twilio API: {e}")

# 2. SECURITY LAYER: Twilio Signature Validation Middleware
validator = RequestValidator(TWILIO_TOKEN)

async def verify_twilio_signature(request: Request):
    signature = request.headers.get("X-Twilio-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Twilio Signature")
    
    form_data = await request.form()
    data = {k: v for k, v in form_data.items()}
    url = str(request.url)
    
    if not validator.validate(url, data, signature):
        raise HTTPException(status_code=403, detail="Invalid Signature. Hacker blocked.")
    return data

# 3. THE BACKGROUND WORKER
def heavy_audio_processing_pipeline(data: dict):
    print("DEBUG: Pipeline just started!")
    # We must create a fresh database session for the background task
    db = SessionLocal() 
    try:
        from_num = data.get("From", "").replace("whatsapp:", "")
        body = data.get("Body", "").strip()
        media_url_0 = data.get("MediaUrl0") 
        
        elder = db.query(api.models.Elder).filter(api.models.Elder.phone == from_num).first()
        if not elder:
            send_whatsapp(from_num, "Namaste! Aapka number register nahi hai.")
            return

        text_to_process = body.lower()
        s3_file_url = None

        if media_url_0:
            audio_response = requests.get(
                media_url_0,
                auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN) if TWILIO_SID else None
            )
            
            if audio_response.status_code in [200, 201]:
                audio_bytes = audio_response.content
                file_name = f"{elder.id}_{uuid.uuid4().hex}.ogg"
                
                # S3 UPLOAD: Fixes the In-Memory RAM crash risk
                if s3_client:
                    s3_client.put_object(
                        Bucket=AWS_BUCKET_NAME,
                        Key=file_name,
                        Body=audio_bytes,
                        ContentType="audio/ogg"
                    )
                    s3_file_url = f"https://{AWS_BUCKET_NAME}.s3.ap-south-1.amazonaws.com/{file_name}"
                
                # GROQ TRANSLATION
                try:
                    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
                    transcript = groq_client.audio.translations.create(
                        model="whisper-large-v3",
                        file=("voice_note.ogg", audio_bytes)
                    )
                    text_to_process = transcript.text
                except Exception as e:
                    print(f"[ERROR] Groq Failed: {e}")
                    text_to_process = "Audio transcription failed."

# 4. AI BRAIN PIPELINE: Gemini + Supabase
        if supabase and gemini_model:
            response = None  # Prevents NameError if Gemini fails
            
            # Safe fallback for s3_file_url if it wasn't defined in Step 3
            if 's3_file_url' not in locals():
                s3_file_url = None
            
            try:
                # A. Save raw transcript to Supabase
                log_res = supabase.table("voice_logs").insert({
                    "patient_id": "0ef65eae-914e-47f3-b9ad-5cb9136fa289", 
                    "raw_text": text_to_process,
                    "audio_url": s3_file_url, 
                    "processed": True
                }).execute()
                log_id = log_res.data[0]['id']

                # B. Ask Gemini to extract symptoms
                prompt = f"""Extract symptoms from: "{text_to_process}". Categorize as NEW SYMPTOM, REPEATED, or WORSENING. Return ONLY a raw JSON array of objects with 'type' and 'label' keys. Do not use markdown."""
                response = gemini_model.generate_content(prompt)
                
            except Exception as e:
                print(f"[ERROR] Gemini or Database Logging Failed: {e}")
                symptoms = []

            # C. JSON Parsing & Email Alerting
            if response:
                try:
                    clean_text = response.text.replace('```json', '').replace('```', '').strip()
                    print(f"DEBUG: Clean text received from Gemini: {clean_text}")
                    
                    symptoms = json.loads(clean_text)
                    print(f"DEBUG: Successfully parsed symptoms array: {symptoms}")
                    
                    if symptoms:
                        print("DEBUG: Active symptoms detected. Initializing alert workflow...")
                        # 1. Get the first symptom label
                        symptom_label = symptoms[0].get('label', 'General Symptom')
                        
                        # 2. Crash-proof check for the patient name
                        if 'elder' in locals() and elder:
                            p_name = getattr(elder, 'name', 'Unknown Patient')
                        else:
                            p_name = 'Prachi (Test Patient)'  # Clean fallback for your active test uuid
                        
                        # 3. Call the email function
                        send_emergency_alert(
                            patient_name=p_name,
                            symptom=symptom_label,
                            raw_message=text_to_process
                        )
                    else:
                        print("DEBUG: Gemini returned an empty symptoms array. No email sent.")
                        
                except Exception as e:
                    print(f"[ERROR] JSON Parse or Alert Dispatch Failed: {e}")
                    symptoms = []
                
# ==========================================
                # 🚨 STEP 3: EMERGENCY ALERT CHECK 🚨
                # ==========================================
                CRITICAL_KEYWORDS = ["chest pain", "shortness of breath", "breathing difficulty", "suffocated", "dizzy", "unconscious", "heavy bleeding", "fainting", "sharp headache"]

                if symptoms:
                    for s in symptoms:
                        tag_label = s.get('label', '').lower()
                        # C. Save extracted tags to Supabase
        try:  # <--- THIS WAS MISSING
            if symptoms:
                tags = [{"log_id": log_id, "patient_id": "0ef65eae-914e-47f3-b9ad-5cb9136fa289", "tag": t.get("label")} for t in symptoms]
                supabase.table("symptom_tags").insert(tags).execute()

            print(f"[SUCCESS] Saved {len(symptoms)} symptoms to AI Brain!")
            
        except Exception as e:
            import traceback 
            print(f"[ERROR] Supabase/Gemini insertion failed: {e}")
            traceback.print_exc()
        
        # 5. GENERATE SAFE TRACKER REPLY
        reply = f"Namaste {elder.name}! Aapka message save ho gaya hai. Aapke caretaker ise jald hi sun lenge. 🙏"
        send_whatsapp(from_num, reply)
        
    except Exception as e:
        print(f"[CRITICAL BACKGROUND ERROR] {e}")
    finally:
        db.close() # Always close the session to prevent memory leaks

# 6. FASTAPI WEBHOOK ROUTE
@app.post("/whatsapp/incoming", dependencies=[Depends(verify_twilio_signature)])
async def whatsapp_incoming(request: Request, background_tasks: BackgroundTasks):
    form_data = await request.form()
    data = {k: v for k, v in form_data.items()}
    
    background_tasks.add_task(heavy_audio_processing_pipeline, data)
    
    twiml_response = MessagingResponse()
    return Response(content=str(twiml_response), media_type="application/xml")

# ─────────────────────────────────────────────
# PHASE 2: NEW AI BRAIN ENDPOINTS
# ─────────────────────────────────────────────
class VoiceNote(BaseModel):
    patient_id: str
    raw_text: str

@app.post("/api/process-log")
async def process_voice_log(note: VoiceNote):
    if not supabase or not gemini_model:
        raise HTTPException(status_code=500, detail="Supabase/Gemini offline.")
        
    try:
        log_res = supabase.table("voice_logs").insert({
            "patient_id": note.patient_id, "raw_text": note.raw_text, "processed": True
        }).execute()
        log_id = log_res.data[0]['id']

        prompt = f"""Extract symptoms from: "{note.raw_text}". Categorize as NEW SYMPTOM, REPEATED, or WORSENING. Return ONLY a raw JSON array of objects with 'type' and 'label' keys. Do not use markdown."""
        response = gemini_model.generate_content(prompt)
        try:
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            symptoms = json.loads(clean_text)
        except Exception as e:
            print(f"[ERROR] JSON Parse Failed: {e}")
            symptoms = []

        if symptoms:
            tags = [{"log_id": log_id, "patient_id": note.patient_id, "tag_type": s['type'], "label": s['label']} for s in symptoms]
            supabase.table("symptom_tags").insert(tags).execute()

        return {"status": "success", "log_id": log_id, "extracted_symptoms": symptoms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────
# DASHBOARD API
# ─────────────────────────────────────────────
@app.get("/api/dashboard/{elder_id}")
def get_dashboard_data(elder_id: int, db: Session = Depends(get_db)):
    elder = db.query(api.models.Elder).filter(api.models.Elder.id == elder_id).first()
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")

    logs = db.query(api.models.HealthLog).filter(api.models.HealthLog.elder_id == elder_id).order_by(api.models.HealthLog.created_at.desc()).limit(10).all()

    formatted_notes = []
    for log in logs:
        sentiment = "negative" if log.mood <= 2 else "positive" if log.mood >= 4 else "neutral"
        symptom_list = log.symptoms if isinstance(log.symptoms, list) else [log.symptoms] if log.symptoms else ["Takleef"]
        
        formatted_notes.append({
            "id": log.id,
            "time": log.created_at.strftime("%I:%M %p"),
            "date": log.created_at.strftime("%b %d"),
            "transcript": log.transcript or log.notes or "No transcript",
            "symptoms": symptom_list,
            "sentiment": sentiment,
            "duration": "0:00",
            "audioUrl": log.audio_url if log.audio_url else "" 
        })

    return {
        "elder": {
            "name": elder.name,
            "relation": "Mother",
            "age": elder.age,
            "status": "stable" if not logs or logs[0].mood >= 3 else "attention",
            "lastCheckin": formatted_notes[0]["time"] if formatted_notes else "Unknown",
            "avatarInitials": "".join([n[0] for n in elder.name.split()])
        },
        "notes": formatted_notes
    }
    
class ElderCreate(BaseModel):
    name: str
    phone: str

@app.post("/api/elders")
def create_elder(elder_in: ElderCreate, db: Session = Depends(get_db)):
    caregiver = db.query(api.models.User).first()
    if not caregiver:
        caregiver = api.models.User(name="Admin User", email="admin@test.com", password_hash="hash")
        db.add(caregiver)
        db.commit()

    new_elder = api.models.Elder(
        name=elder_in.name,
        phone=elder_in.phone,
        age=65, 
        city="Unknown",
        caregiver_id=caregiver.id
    )
    db.add(new_elder)
    db.commit()
    db.refresh(new_elder)
    
    return {"status": "success", "elder_id": new_elder.id}

# ─────────────────────────────────────────────
# ML SCHEMAS & PREDICTION LOGIC
# ─────────────────────────────────────────────
class PredictRequest(BaseModel):
    symptoms: list[str]
    age: Optional[int] = None
    sex: Optional[str] = None

    @field_validator("symptoms")
    @classmethod
    def symptoms_not_empty(cls, v):
        if not v:
            raise ValueError("At least one symptom is required.")
        return [s.strip().lower().replace(" ", "_") for s in v]

class PredictionResult(BaseModel):
    disease: str
    confidence: float
    confidence_label: str

class PredictResponse(BaseModel):
    risk_level: str
    top_predictions: list[PredictionResult]
    unclear: bool
    disclaimer: str
    next_steps: list[str]
    unrecognized_symptoms: list[str]

class InjuryRequest(BaseModel):
    body_part: str = "ankle"
    mechanism: str = "twist"
    can_weight_bear: bool = True
    immediate_swelling: bool = False
    point_tenderness: bool = False
    audible_crack: bool = False
    range_of_motion_lost: bool = False
    bruising_present: bool = False
    tenderness_medial_malleolus: Optional[bool] = None
    tenderness_lateral_malleolus: Optional[bool] = None
    tenderness_navicular: Optional[bool] = None
    tenderness_base_5th_metatarsal: Optional[bool] = None
    age: Optional[int] = None
    isolated_patella_tenderness: Optional[bool] = None
    fibula_head_tenderness: Optional[bool] = None
    cannot_flex_knee_90: Optional[bool] = None

class InjuryResponse(BaseModel):
    fracture_probability: str
    clinical_rule_applied: str
    findings: list[str]
    recommendation: str
    action_steps: list[str]
    disclaimer: str

class FeedbackRequest(BaseModel):
    session_id: str
    predicted_disease: str
    actual_diagnosis: Optional[str] = None
    was_helpful: bool

RED_CONDITIONS = {
    "heart attack", "myocardial infarction", "stroke", "paralysis (brain)",
    "pneumonia", "septicemia", "dengue", "malaria",
    "typhoid fever", "hepatitis e", "liver failure",
}

YELLOW_CONDITIONS = {
    "jaundice", "hepatitis b", "hepatitis c", "hepatitis d", "hepatitis a",
    "tuberculosis", "diabetes", "hypertension", "urinary tract infection",
    "cervical spondylosis", "peptic ulcer disease", "hypothyroidism",
    "hyperthyroidism", "hypoglycemia",
}

def assign_risk(disease: str, confidence: float, age: Optional[int] = None) -> str:
    d = disease.lower()
    base_risk = "GREEN"
    if d in RED_CONDITIONS:
        base_risk = "RED"
    elif d in YELLOW_CONDITIONS:
        base_risk = "YELLOW"

    if age and age >= 65 and base_risk == "GREEN":
        base_risk = "YELLOW"
    if age and age >= 65 and base_risk == "YELLOW":
        base_risk = "RED"

    return base_risk

def confidence_label(p: float) -> str:
    if p >= 0.75:
        return "HIGH"
    elif p >= 0.50:
        return "MODERATE"
    return "LOW"

def build_next_steps(risk: str, disease: str) -> list[str]:
    if risk == "RED":
        return [
            "Seek emergency medical care immediately.",
            "Do not self-medicate. Call 112 or go to the nearest emergency room.",
            "Share this preliminary assessment with the attending doctor.",
        ]
    elif risk == "YELLOW":
        return [
            "Consult a doctor within 24-48 hours.",
            "Avoid physical exertion until reviewed by a professional.",
            "Monitor symptoms — if they worsen, escalate to emergency care.",
        ]
    return [
        "Schedule a routine doctor visit to confirm this assessment.",
        "Rest and stay hydrated.",
        "Return to this app if symptoms worsen.",
    ]

def _build_injury_response(prob: str, rule: str, findings: list[str]) -> InjuryResponse:
    if prob == "HIGH":
        recommendation = "HIGH fracture probability. Go to an emergency room now. Do not put weight on the injury."
        steps = [
            "Do not walk on or use the injured limb.",
            "Immobilize with a splint, firm pillow, or rolled clothing.",
            "Apply ice wrapped in cloth — NOT directly on skin.",
            "Go to the nearest emergency room or call 112.",
            "An X-ray is required to confirm or rule out fracture.",
        ]
    elif prob == "MEDIUM":
        recommendation = "UNCLEAR — fracture cannot be ruled out. Visit urgent care within 24 hours."
        steps = [
            "Avoid putting weight on the injury until assessed.",
            "Apply RICE: Rest, Ice (20 min on/off), Compression, Elevation.",
            "Take OTC pain reliever (Paracetamol) if no contraindications.",
            "Visit orthopedic clinic within 24 hours.",
            "Watch for: worsening pain, numbness, color change — escalate immediately.",
        ]
    else:
        recommendation = "LOW fracture probability. Likely sprain. Follow RICE protocol. Monitor 48 hours."
        steps = [
            "Rest — avoid painful activities for 48-72 hours.",
            "Ice — 15-20 minutes every 2-3 hours for first 48 hours.",
            "Compression — elastic bandage, firm but not tight.",
            "Elevation — raise above heart level when resting.",
            "OTC pain relief: Paracetamol 500mg with food.",
            "Return if: pain worsens after 48 hours, swelling increases, or cannot bear weight.",
        ]

    return InjuryResponse(
        fracture_probability=prob,
        clinical_rule_applied=rule,
        findings=findings,
        recommendation=recommendation,
        action_steps=steps,
        disclaimer="IMPORTANT: This is a preliminary assessment only. It cannot replace a physical examination or X-ray. A qualified doctor must confirm or rule out fracture.",
    )

def triage_ankle(req: InjuryRequest) -> InjuryResponse:
    findings = []
    flags = 0
    if req.tenderness_medial_malleolus: findings.append("Tenderness at medial malleolus"); flags += 2
    if req.tenderness_lateral_malleolus: findings.append("Tenderness at lateral malleolus"); flags += 2
    if req.tenderness_navicular: findings.append("Tenderness at navicular"); flags += 2
    if req.tenderness_base_5th_metatarsal: findings.append("Tenderness at base of 5th metatarsal"); flags += 2
    if not req.can_weight_bear: findings.append("Cannot bear weight"); flags += 3
    if req.immediate_swelling: findings.append("Immediate swelling"); flags += 1
    if req.audible_crack: findings.append("Audible crack"); flags += 2
    if req.point_tenderness: findings.append("Point tenderness over bone"); flags += 1
    if req.mechanism == "direct_impact": findings.append("Direct impact mechanism"); flags += 1
    if not findings: findings.append("No Ottawa Rule criteria met. Likely sprain.")
    prob = "HIGH" if flags >= 5 else ("MEDIUM" if flags >= 2 else "LOW")
    return _build_injury_response(prob, "Ottawa Ankle/Foot Rules", findings)

def triage_knee(req: InjuryRequest) -> InjuryResponse:
    findings = []
    flags = 0
    if req.age and req.age > 55: findings.append("Age >55"); flags += 2
    if req.isolated_patella_tenderness: findings.append("Isolated patella tenderness"); flags += 2
    if req.fibula_head_tenderness: findings.append("Fibula head tenderness"); flags += 2
    if req.cannot_flex_knee_90: findings.append("Cannot flex knee to 90 degrees"); flags += 2
    if not req.can_weight_bear: findings.append("Cannot bear weight"); flags += 3
    if req.immediate_swelling: findings.append("Immediate swelling"); flags += 1
    if req.audible_crack: findings.append("Audible crack"); flags += 2
    if not findings: findings.append("No Ottawa Knee Rule criteria met.")
    prob = "HIGH" if flags >= 5 else ("MEDIUM" if flags >= 2 else "LOW")
    return _build_injury_response(prob, "Ottawa Knee Rules", findings)

def triage_general(req: InjuryRequest) -> InjuryResponse:
    findings = []
    flags = 0
    if not req.can_weight_bear: findings.append("Inability to bear weight"); flags += 3
    if req.audible_crack: findings.append("Audible crack or pop"); flags += 2
    if req.immediate_swelling: findings.append("Swelling within 1 hour"); flags += 2
    if req.point_tenderness: findings.append("Pinpoint tenderness over bone"); flags += 2
    if req.range_of_motion_lost: findings.append("Complete loss of range of motion"); flags += 2
    if req.mechanism == "direct_impact": findings.append("Direct impact mechanism"); flags += 1
    if req.bruising_present and req.immediate_swelling: findings.append("Bruising + immediate swelling"); flags += 1
    if not findings: findings.append("Minimal fracture indicators. Likely sprain.")
    prob = "HIGH" if flags >= 6 else ("MEDIUM" if flags >= 3 else "LOW")
    return _build_injury_response(prob, "General Sprain vs Fracture Indicators", findings)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL_LOADED,
        "model_type": MODEL_REPORT.get("best_model", "none"),
        "disease_count": len(le.classes_) if MODEL_LOADED else 0,
        "symptom_count": len(SYMPTOM_COLS),
        "version": "2.0.0",
    }

@app.get("/symptoms")
def list_symptoms():
    return {"symptoms": SYMPTOM_COLS, "count": len(SYMPTOM_COLS)}

@app.get("/diseases")
def list_diseases():
    if not MODEL_LOADED:
        raise HTTPException(503, "Model not loaded. Run model/train.py first.")
    return {"diseases": list(le.classes_), "count": len(le.classes_)}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if not MODEL_LOADED:
        raise HTTPException(503, "Model not loaded. Run model/train.py first.")

    unrecognized = [s for s in req.symptoms if s not in SYMPTOM_SET]
    recognized = [s for s in req.symptoms if s in SYMPTOM_SET]

    feature_vector = np.zeros(len(SYMPTOM_COLS))
    for symptom in recognized:
        feature_vector[SYMPTOM_COLS.index(symptom)] = 1

    proba = model.predict_proba([feature_vector])[0]
    top3_indices = np.argsort(proba)[::-1][:3]

    predictions = [
        PredictionResult(
            disease=le.inverse_transform([i])[0],
            confidence=round(float(proba[i]), 4),
            confidence_label=confidence_label(proba[i]),
        )
        for i in top3_indices
    ]

    top_disease = predictions[0].disease
    top_conf = predictions[0].confidence
    unclear = top_conf < 0.60

    risk = assign_risk(top_disease, top_conf, req.age)
    next_steps = build_next_steps(risk, top_disease)

    return PredictResponse(
        risk_level=risk,
        top_predictions=predictions,
        unclear=unclear,
        disclaimer="This is a preliminary AI-assisted assessment, not a medical diagnosis. Consult a qualified doctor before making any health decisions.",
        next_steps=next_steps,
        unrecognized_symptoms=unrecognized,
    )

@app.post("/predict/injury", response_model=InjuryResponse)
def predict_injury(req: InjuryRequest):
    bp = req.body_part.lower()
    if bp in ("ankle", "foot"):
        return triage_ankle(req)
    elif bp in ("knee",):
        return triage_knee(req)
    else:
        return triage_general(req)

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "session_id": req.session_id,
        "predicted": req.predicted_disease,
        "actual": req.actual_diagnosis,
        "helpful": req.was_helpful,
    }
    feedback_file = Path(__file__).parent.parent / "data" / "feedback.jsonl"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    with open(feedback_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"status": "recorded", "message": "Thank you. Your feedback improves future predictions."}

@app.get("/get-sql")
def generate_sql():
    sql = "-- SQLAlchemy Models --\n\n"
    for table in api.models.Base.metadata.sorted_tables:
        sql += str(CreateTable(table).compile(dialect=postgresql.dialect())).strip() + ";\n\n"
        
    sql += "-- Raw Supabase Tables --\n\n"
    sql += "CREATE TABLE IF NOT EXISTS voice_logs (\n  id SERIAL PRIMARY KEY,\n  patient_id VARCHAR,\n  raw_text TEXT,\n  processed BOOLEAN,\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\n"
    sql += "CREATE TABLE IF NOT EXISTS symptom_tags (\n  id SERIAL PRIMARY KEY,\n  log_id INTEGER,\n  patient_id VARCHAR,\n  tag_type VARCHAR,\n  label VARCHAR,\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n"
    
    return PlainTextResponse(content=sql)