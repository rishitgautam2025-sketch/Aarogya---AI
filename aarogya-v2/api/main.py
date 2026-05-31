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

from dotenv import load_dotenv
load_dotenv()

import json
import os
import traceback
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from .database import engine
from . import models

import joblib
import numpy as np
import requests
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
# --- NEW PHASE 2 IMPORTS ---
from supabase import create_client, Client
import google.generativeai as genai

# Local imports
from api.routers import whatsapp
from api.scheduler import start_scheduler
from api.database import Base, engine, get_db
import api.models
from api.routers.auth import router as auth_router
from api.routers.elder_monitor import router as elder_monitor_router


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

# ─────────────────────────────────────────────
# APP SETUP & MIDDLEWARE (Cleaned & Unified)
# ─────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)

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
# ✅ SECURED CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aarogya-ai-navy.vercel.app",   # Your live Vercel frontend
        "http://localhost:5173",                # Local React development
        "http://127.0.0.1:5173",                # Local React development (alt)
    ],
    allow_credentials=True,
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

# Create SQLite tables on first startup
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(auth_router)
app.include_router(elder_monitor_router)
app.include_router(whatsapp.router)


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
# WHATSAPP WEBHOOK
# ─────────────────────────────────────────────

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

def send_whatsapp(to: str, message: str):
    if not TWILIO_SID or not TWILIO_TOKEN:
        print(f"[ERROR] Twilio not configured. SID: {TWILIO_SID}, TOKEN: {TWILIO_TOKEN}")
        return
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    payload = {"From": TWILIO_NUMBER, "To": f"whatsapp:{to}", "Body": message}
    
    print(f"[DEBUG] Attempting to send WhatsApp to {to}...")
    
    try:
        response = requests.post(url, data=payload, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=10)
        print(f"[DEBUG] Twilio API Response: {response.status_code} - {response.text[:150]}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Twilio API: {e}")
        
def extract_symptoms_for_whatsapp(text: str):
    """Helper function to run text through Gemini"""
    if not text.strip(): return []
    try:
        prompt = f"""Extract symptoms from: "{text}". Categorize as NEW SYMPTOM, REPEATED, or WORSENING. Return ONLY a raw JSON array of objects with 'type' and 'label' keys. Do not use markdown."""
        response = gemini_model.generate_content(prompt)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        print(f"[ERROR] Gemini Extraction Failed: {e}")
        return []

@app.post("/whatsapp/incoming")
async def whatsapp_incoming(request: Request, db: Session = Depends(get_db)):
    from api.models import Elder, HealthLog
    
    form = await request.form()
    print(f"[DEBUG] Incoming WhatsApp from: {form.get('From')}") 
    
    from_num = form.get("From", "").replace("whatsapp:", "")
    body = form.get("Body", "").strip()
    media_url_0 = form.get("MediaUrl0") 
    
    elder = db.query(Elder).filter(Elder.phone == from_num).first()
    if not elder:
        return {"reply": "Namaste! Aapka number register nahi hai. Apne bachche se contact karein."}

    # --- 1. DOWNLOAD AUDIO IF IT EXISTS ---
    local_audio_path = None
    if media_url_0:
        audio_response = requests.get(media_url_0)
        if audio_response.status_code == 200:
            filename = f"{uuid.uuid4()}.ogg"
            filepath = os.path.join("media", filename)
            with open(filepath, "wb") as f:
                f.write(audio_response.content)
            local_audio_path = f"media/{filename}"

    # --- 2. PARSE MOOD & SYMPTOMS (GEMINI UPGRADE) ---
    text = body.lower()
    extracted_tags = extract_symptoms_for_whatsapp(body)
    
    # Extract just the labels to save into your database
    symptoms = [tag['label'] for tag in extracted_tags] if extracted_tags else []
    
    mood = 3 # Default Neutral
    if extracted_tags:
        if any(tag['type'] == 'WORSENING' for tag in extracted_tags):
            mood = 1
        elif any(tag['type'] == 'NEW SYMPTOM' for tag in extracted_tags):
            mood = 2
    elif "theek" in text or "acha" in text or "badhiya" in text:
        mood = 4
    
    # --- 3. SAVE TO DATABASE ---
    log = HealthLog(
        elder_id=elder.id,
        mood=mood,
        symptoms=symptoms,
        notes=body,
        transcript=body, 
        audio_url=local_audio_path, 
        source="whatsapp",
        log_date=date.today(),
        is_daily_summary=False,
        logged_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    # --- 4. GENERATE REPLY ---
    if mood >= 4 and not symptoms:
        reply = f"Namaste {elder.name}! Aap theek hain, yeh sunke acha laga. Aur kuch ho toh batana. 🙏"
    elif mood <= 2:
        symptom_text = ", ".join(symptoms) if symptoms else "kuch taklif"
        reply = f"Namaste {elder.name}! Aapne bataya ki {symptom_text}. Main note kar liya. Aram karein. 🏥"
    else:
        reply = f"Namaste {elder.name}! Update mil gaya. Dhanyawaad! 🙏"
    
    send_whatsapp(from_num, reply)
    return {"status": "saved", "mood": mood, "symptoms": symptoms}


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
        # Save raw text
        log_res = supabase.table("voice_logs").insert({
            "patient_id": note.patient_id, "raw_text": note.raw_text, "processed": True
        }).execute()
        log_id = log_res.data[0]['id']

        # Extract tags
        prompt = f"""Extract symptoms from: "{note.raw_text}". Categorize as NEW SYMPTOM, REPEATED, or WORSENING. Return ONLY a raw JSON array of objects with 'type' and 'label' keys. Do not use markdown."""
        response = gemini_model.generate_content(prompt)
        try:
            # Strip out any annoying markdown backticks before parsing
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            symptoms = json.loads(clean_text)
        except Exception as e:
            print(f"[ERROR] JSON Parse Failed: {e}")
            symptoms = []

        # Save tags
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
            "duration": "0:00",  # React will dynamically overwrite this when it loads the file
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

@app.get("/setup-db")
def force_setup_db():
    # Explicitly import the models so SQLAlchemy wakes up and sees them!
    from api.models import User, Elder, HealthLog
    from api.database import Base, engine
    
    try:
        Base.metadata.create_all(bind=engine)
        return {"status": "success", "message": "Supabase tables forcefully built!"}
    except Exception as e:
        return {"status": "error", "error_details": str(e)}