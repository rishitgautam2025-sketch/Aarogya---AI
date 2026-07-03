"""
Aarogya AI V2 — FastAPI REST API
"""
from click import prompt
from dotenv import load_dotenv
load_dotenv()

import json
import traceback
import joblib
import numpy as np
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql

# Internal imports
from api.database import engine, get_db
import api.models
from api.scheduler import start_scheduler
# Change this import
from api.config import supabase, gemini_client, AAROGYA_MODEL

# Routers
from api.routers.auth import router as auth_router
from api.routers.elder_monitor import router as elder_monitor_router
from api.routers import reports, onboarding
from api.routers.whatsapp import router as whatsapp_router

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────
api.models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Aarogya AI V2",
    description="Health intelligence API — symptom triage, injury assessment, and remote elder care",
    version="2.0.0",
)

os.makedirs("media", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    start_scheduler()

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    print(traceback.format_exc())  # always logged server-side
    if DEBUG_MODE:
        return JSONResponse(
            status_code=500,
            content={
                "CRASH_MESSAGE": str(exc),
                "EXACT_LOCATION": traceback.format_exc().splitlines()[-3:]
            }
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."}
    )
    
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Aarogya AI is running.",
        "docs": "Visit /docs for the API Swagger documentation."
    }

# Register all Routers
app.include_router(auth_router)
app.include_router(elder_monitor_router)
app.include_router(reports.router)
app.include_router(onboarding.router)
app.include_router(whatsapp_router) # <--- WhatsApp API successfully linked!

# ─────────────────────────────────────────────
# LOAD ML ARTIFACTS
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
# NEW AI BRAIN ENDPOINTS
# ─────────────────────────────────────────────
class VoiceNote(BaseModel):
    patient_id: str
    raw_text: str

@app.post("/api/process-log")
async def process_voice_log(note: VoiceNote):
    if not supabase or not gemini_client:
        raise HTTPException(status_code=500, detail="Supabase/Gemini offline.")
        
    try:
        # 1. Insert Log to Supabase
        log_res = supabase.table("voice_logs").insert({
            "patient_id": note.patient_id, 
            "raw_text": note.raw_text, 
            "processed": True
        }).execute()
        
        # We ensure log_id is defined here
        log_id = log_res.data[0]['id']

        # 2. Call Gemini
        prompt = f"""You are a medical triage AI.
        Transcript: "{note.raw_text}"
        Task: Extract symptoms. Categorize as NEW SYMPTOM, REPEATED, or WORSENING. Analyze severity and set "is_emergency" to true if highly critical.
        Return ONLY a raw JSON array of objects with keys: 'type', 'label', and 'is_emergency' (boolean)."""
        
        response = gemini_client.models.generate_content(
            model=AAROGYA_MODEL,
            contents=prompt
        )

        # 3. Parse Symptoms
        try:
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            if not clean_text.startswith('['): clean_text = f"[{clean_text}]"
            symptoms = json.loads(clean_text)
        except Exception:
            symptoms = []

        # 4. Save Symptoms if found
        if symptoms:
            tags = [{"log_id": log_id, "patient_id": note.patient_id, "tag_type": s.get('type', 'NEW SYMPTOM'), "label": s.get('label', 'Symptom')} for s in symptoms]
            supabase.table("symptom_tags").insert(tags).execute()

        return {"status": "success", "log_id": log_id, "extracted_symptoms": symptoms}

    except Exception as e:
        # This catches any errors and ensures the code is structurally valid
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
            "relation": elder.relation or "Family",
            "age": elder.age,
            "status": "stable" if not logs or logs[0].mood >= 3 else "attention",
            "lastCheckin": formatted_notes[0]["time"] if formatted_notes else "Unknown",
            "avatarInitials": "".join([n[0] for n in elder.name.split()])
        },
        "notes": formatted_notes
    }

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
    if d in RED_CONDITIONS: base_risk = "RED"
    elif d in YELLOW_CONDITIONS: base_risk = "YELLOW"
    if age and age >= 65 and base_risk == "GREEN": base_risk = "YELLOW"
    if age and age >= 65 and base_risk == "YELLOW": base_risk = "RED"
    return base_risk

def confidence_label(p: float) -> str:
    if p >= 0.75: return "HIGH"
    elif p >= 0.50: return "MODERATE"
    return "LOW"

def build_next_steps(risk: str, disease: str) -> list[str]:
    if risk == "RED":
        return ["Seek emergency medical care immediately.", "Do not self-medicate. Call 112 or go to the nearest emergency room.", "Share this preliminary assessment with the attending doctor."]
    elif risk == "YELLOW":
        return ["Consult a doctor within 24-48 hours.", "Avoid physical exertion until reviewed by a professional.", "Monitor symptoms — if they worsen, escalate to emergency care."]
    return ["Schedule a routine doctor visit to confirm this assessment.", "Rest and stay hydrated.", "Return to this app if symptoms worsen."]

def _build_injury_response(prob: str, rule: str, findings: list[str]) -> InjuryResponse:
    if prob == "HIGH":
        recommendation = "HIGH fracture probability. Go to an emergency room now. Do not put weight on the injury."
        steps = ["Do not walk on or use the injured limb.", "Immobilize with a splint, firm pillow, or rolled clothing.", "Go to the nearest emergency room or call 112."]
    elif prob == "MEDIUM":
        recommendation = "UNCLEAR — fracture cannot be ruled out. Visit urgent care within 24 hours."
        steps = ["Avoid putting weight on the injury until assessed.", "Apply RICE: Rest, Ice (20 min on/off), Compression, Elevation.", "Visit orthopedic clinic within 24 hours."]
    else:
        recommendation = "LOW fracture probability. Likely sprain. Follow RICE protocol. Monitor 48 hours."
        steps = ["Rest — avoid painful activities for 48-72 hours.", "Ice — 15-20 minutes every 2-3 hours for first 48 hours.", "Return if: pain worsens after 48 hours, swelling increases, or cannot bear weight."]

    return InjuryResponse(
        fracture_probability=prob,
        clinical_rule_applied=rule,
        findings=findings,
        recommendation=recommendation,
        action_steps=steps,
        disclaimer="IMPORTANT: This is a preliminary assessment only. It cannot replace a physical examination or X-ray.",
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
    if not findings: findings.append("No Ottawa Knee Rule criteria met.")
    prob = "HIGH" if flags >= 5 else ("MEDIUM" if flags >= 2 else "LOW")
    return _build_injury_response(prob, "Ottawa Knee Rules", findings)

def triage_general(req: InjuryRequest) -> InjuryResponse:
    findings = []
    flags = 0
    if not req.can_weight_bear: findings.append("Inability to bear weight"); flags += 3
    if req.audible_crack: findings.append("Audible crack or pop"); flags += 2
    if req.immediate_swelling: findings.append("Swelling within 1 hour"); flags += 2
    if not findings: findings.append("Minimal fracture indicators. Likely sprain.")
    prob = "HIGH" if flags >= 6 else ("MEDIUM" if flags >= 3 else "LOW")
    return _build_injury_response(prob, "General Sprain vs Fracture Indicators", findings)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL_LOADED,
        "model_type": MODEL_REPORT.get("best_model", "none"),
        "version": "2.0.0",
    }

@app.get("/symptoms")
def list_symptoms():
    return {"symptoms": SYMPTOM_COLS, "count": len(SYMPTOM_COLS)}

@app.get("/diseases")
def list_diseases():
    if not MODEL_LOADED: raise HTTPException(503, "Model not loaded.")
    return {"diseases": list(le.classes_), "count": len(le.classes_)}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if not MODEL_LOADED: raise HTTPException(503, "Model not loaded.")
    unrecognized = [s for s in req.symptoms if s not in SYMPTOM_SET]
    recognized = [s for s in req.symptoms if s in SYMPTOM_SET]

    feature_vector = np.zeros(len(SYMPTOM_COLS))
    for symptom in recognized: feature_vector[SYMPTOM_COLS.index(symptom)] = 1

    proba = model.predict_proba([feature_vector])[0]
    top3_indices = np.argsort(proba)[::-1][:3]
    predictions = [PredictionResult(disease=le.inverse_transform([i])[0], confidence=round(float(proba[i]), 4), confidence_label=confidence_label(proba[i])) for i in top3_indices]

    top_disease = predictions[0].disease
    top_conf = predictions[0].confidence
    risk = assign_risk(top_disease, top_conf, req.age)
    
    return PredictResponse(
        risk_level=risk,
        top_predictions=predictions,
        unclear=top_conf < 0.60,
        disclaimer="This is a preliminary AI-assisted assessment, not a medical diagnosis.",
        next_steps=build_next_steps(risk, top_disease),
        unrecognized_symptoms=unrecognized,
    )

@app.post("/predict/injury", response_model=InjuryResponse)
def predict_injury(req: InjuryRequest):
    bp = req.body_part.lower()
    if bp in ("ankle", "foot"): return triage_ankle(req)
    elif bp in ("knee",): return triage_knee(req)
    else: return triage_general(req)

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    entry = {"timestamp": datetime.utcnow().isoformat(), "session_id": req.session_id, "predicted": req.predicted_disease, "actual": req.actual_diagnosis, "helpful": req.was_helpful}
    feedback_file = Path(__file__).parent.parent / "data" / "feedback.jsonl"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    with open(feedback_file, "a") as f: f.write(json.dumps(entry) + "\n")
    return {"status": "recorded", "message": "Feedback saved."}

@app.get("/get-sql")
def generate_sql():
    sql = "-- SQLAlchemy Models --\n\n"
    for table in api.models.Base.metadata.sorted_tables:
        sql += str(CreateTable(table).compile(dialect=postgresql.dialect())).strip() + ";\n\n"
    return PlainTextResponse(content=sql)