"""
Elder Monitor Router — SECURED with JWT auth + anomaly detection.
"""

import openai
import google.generativeai as genai
import json
import os

# API Configurations
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

import os
import requests
import json
import openai
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import HealthLog, Elder
from datetime import datetime, date
from twilio.rest import Client
from requests.auth import HTTPBasicAuth

load_dotenv()

# Setup AI
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
client = Client(TWILIO_SID, TWILIO_TOKEN)

DISCLAIMER = "\n\n(Note: This is a summary of your daily symptom log for your personal records. It is not medical advice.)"

# --- THE AI BRAIN ---
async def transcribe_and_analyze(audio_path):
    # Transcribe with Whisper
    with open(audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    text = transcript["text"]

    # Analyze with Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Extract symptoms from this text: '{text}'. Return a short summary."
    response = model.generate_content(prompt)
    return text, response.text

@router.post("/incoming")
async def incoming(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    from_num = form.get("From", "").replace("whatsapp:", "")
    body = form.get("Body", "").strip()
    media_url = form.get("MediaUrl0")
    media_sid = form.get("MediaSid0")
    
    # 1. GATEKEEPER
    if not body and not media_url:
        return {"status": "ignored"}

    # 2. AUDIO HANDLING
    text = body.lower()
    if media_url and "audio" in form.get("MediaContentType0", ""):
        # Download
        audio_path = "temp_note.ogg"
        r = requests.get(media_url, auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN))
        with open(audio_path, "wb") as f: f.write(r.content)
        
        # Transcribe
        text, ai_summary = await transcribe_and_analyze(audio_path)
        body = f"Voice note: {text}. Analysis: {ai_summary}"
        
        # Cleanup
        if os.path.exists(audio_path): os.remove(audio_path)
        client.api.v2010.account(TWILIO_SID).media(media_sid).delete()

    # 3. SAFETY SHIELD
    emergency_keywords = ["chest pain", "saans", "breathless", "bleeding", "emergency"]
    if any(word in text for word in emergency_keywords):
        return {"reply": "🚨 EMERGENCY ALERT: Please call for help."}

    # 4. SAVE & REPLY (Your existing logic here...)
    # [Insert your DB save logic from before]
    
    return {"status": "saved"}
async def transcribe_and_analyze(audio_file_path):
    # 1. Transcribe with Whisper
    with open(audio_file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        text = transcript["text"]
    
    print(f"📝 Transcription: {text}")

    # 2. Analyze with Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Extract clinical vitals from this text: "{text}"
    Return ONLY valid JSON with keys: 'temperature', 'heart_rate', 'systolic_bp', 'diastolic_bp'.
    If a value is missing, use null.
    """
    response = model.generate_content(prompt)
    
    # Clean the output to ensure it is valid JSON
    clean_json = response.text.replace('```json', '').replace('```', '').strip()
    vitals_json = json.loads(clean_json)
    
    print(f"🧠 AI Extracted Vitals: {vitals_json}")
    return text, vitals_json
from api.auth import get_current_user
from api.routers.whatsapp import send_whatsapp
from fastapi import APIRouter, Depends, HTTPException, Request, Form, Response
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import httpx

from api.database import get_db
from api.models import Elder, User, HealthLog, Alert
from api.auth import get_current_active_user

router = APIRouter(prefix="/elder-monitor", tags=["Elder Monitor"])
def test_fetch_elders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return db.query(Elder).filter(Elder.caregiver_id == current_user.id).all()

GEOAPIFY_KEY = os.getenv("GEOAPIFY_KEY", "c7c39837c677431cb5568b46a9e4f6a7")


# ── Pydantic schemas ──────────────────────────────────────────────

class ElderCreate(BaseModel):
    name: str
    age: int
    city: str
    phone: Optional[str] = None  # <--- ADD THIS EXACT LINE!
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    known_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    emergency_contact: Optional[str] = None

from typing import List, Optional
from pydantic import BaseModel

class HealthLogCreate(BaseModel):
    elder_id: int
    
    # Qualitative check-in
    feeling_today: Optional[str] = None
    appetite: Optional[str] = None
    mobility: Optional[str] = None
    had_fall: Optional[bool] = False
    new_pain: Optional[bool] = False
    new_pain_location: Optional[str] = None
    
    # Clinical vitals (Optional)
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[float] = None
    blood_pressure_diastolic: Optional[float] = None
    
    # Symptoms
    symptoms: Optional[List[str]] = []
    symptom_severity: Optional[str] = "mild"
    notes: Optional[str] = None


# ── Security helper ───────────────────────────────────────────────

def get_elder_or_404(elder_id: int, user: User, db: Session):
    """Ensure the elder exists AND belongs to the currently authenticated user."""
    elder = db.query(Elder).filter(Elder.id == elder_id).first()
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    if elder.caregiver_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this elder's data")
    return elder


# ── Anomaly detection ─────────────────────────────────────────────

def detect_anomaly(log: HealthLogCreate) -> tuple[bool, str, str]:
    """
    Returns: (is_anomaly, severity, message)
    """
    warnings = []
    severity = "YELLOW"

    # 1. Qualitative Red Flags (Critical for rural triage)
    if log.had_fall:
        warnings.append("Patient experienced a fall today.")
        severity = "RED"
        
    if log.mobility == "Cannot Get Up":
        warnings.append("Patient is unable to get up out of bed/chair.")
        severity = "RED"
        
    if log.feeling_today == "Very Poor" and log.appetite == "Not Eating":
        warnings.append("Patient reports feeling very poor with complete loss of appetite.")
        severity = "RED"

    if log.new_pain:
        loc = f" in {log.new_pain_location}" if log.new_pain_location else ""
        warnings.append(f"Reported new onset of pain{loc}.")

    # 2. Clinical Vitals (If provided by ASHA worker)
    if log.temperature:
        if log.temperature > 38.5:  # ~101.3 F
            warnings.append(f"High fever detected ({log.temperature}°C).")
            severity = "RED" if log.temperature > 39.5 else "YELLOW"
        elif log.temperature < 35.0:
            warnings.append(f"Hypothermia risk ({log.temperature}°C).")
            severity = "RED"

    if log.blood_pressure_systolic and log.blood_pressure_diastolic:
        if log.blood_pressure_systolic > 180 or log.blood_pressure_diastolic > 120:
            warnings.append(f"Hypertensive crisis ({log.blood_pressure_systolic}/{log.blood_pressure_diastolic}).")
            severity = "RED"
        elif log.blood_pressure_systolic < 90:
            warnings.append(f"Dangerously low blood pressure ({log.blood_pressure_systolic}/{log.blood_pressure_diastolic}).")
            severity = "RED"

    if warnings:
        return True, severity, " | ".join(warnings)
    
    return False, "GREEN", "No immediate anomalies detected."


# ── Routes ───────────────────────────────────────────────────────

@router.get("/my-elders")
def get_my_elders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Fetch all patients belonging to the logged-in caregiver
    elders = db.query(Elder).filter(Elder.caregiver_id == current_user.id).all()
    return elders

@router.post("/register")
def register_elder(
    payload: ElderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    elder = Elder(caregiver_id=current_user.id, **payload.model_dump())
    db.add(elder)
    db.commit()
    db.refresh(elder)
    return {"status": "registered", "elder_id": elder.id, "name": elder.name}


@router.post("/log")
def log_health(payload: HealthLogCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Verify the patient belongs to the current user
    elder = db.query(Elder).filter(Elder.id == payload.elder_id).first()
    if not elder:
        raise HTTPException(status_code=404, detail="Patient not found")

    # 2. Run the AI anomaly detection
    is_anomaly, severity, message = detect_anomaly(payload)

    # 3. Save the new qualitative data to the database
    new_log = HealthLog(
        elder_id=payload.elder_id,
        feeling_today=payload.feeling_today,
        appetite=payload.appetite,
        mobility=payload.mobility,
        had_fall=payload.had_fall,
        new_pain=payload.new_pain,
        new_pain_location=payload.new_pain_location,
        temperature=payload.temperature,
        blood_pressure_systolic=payload.blood_pressure_systolic,
        blood_pressure_diastolic=payload.blood_pressure_diastolic,
        symptoms=payload.symptoms,
        symptom_severity=payload.symptom_severity,
        notes=payload.notes,
        risk_level=severity,
        ai_recommendation=message if is_anomaly else "Monitor normally."
    )
    
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
# --- THE WHATSAPP TRIGGER & CLARIFICATION LOOP ---
    if elder and elder.phone:
        # Safely get the risk level
        risk = getattr(new_log, 'risk_level', 'normal').lower()

        # 1. Check for Moderate / Clarification FIRST (Intercepts the anomaly flag)
        if risk in ["moderate", "medium", "borderline", "elevated", "yellow"]:
            alert_message = f"🟡 Aarogya AI Notice: Vitals for {elder.name} are slightly abnormal (Temp: {new_log.temperature}°C). Can you please double-check their vitals and log them again to be safe?"
            try:
                send_whatsapp(to=elder.phone, message=alert_message)
                print("Clarification request sent.")
            except Exception as e:
                print(f"Failed to trigger WhatsApp: {e}")
        
        # 2. High Risk Alert (The Emergency)
        elif risk == "high" or is_anomaly:
            alert_message = f"🚨 Aarogya AI Alert: HIGH RISK detected for {elder.name}. Issue: {new_log.ai_recommendation}"
            try:
                send_whatsapp(to=elder.phone, message=alert_message)
                print("High risk alert sent.")
            except Exception as e:
                print(f"Failed to trigger WhatsApp: {e}")
        # ---------------------------------------

        
    alert_data = None
    if is_anomaly:
        from api.models import Alert 
        new_alert = Alert(
            elder_id=payload.elder_id,
            alert_type="MEDICAL_ANOMALY",  # <--- Add this missing line!
            severity=severity,
            message=message
        )
        
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        alert_data = {"id": new_alert.id, "severity": new_alert.severity, "message": new_alert.message}

    return {
        "message": "Health logged successfully", 
        "log_id": new_log.id,
        "alert_triggered": is_anomaly,
        "alert": alert_data
    }


@router.get("/history/{elder_id}")
def get_history(
    elder_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    elder = get_elder_or_404(elder_id, current_user, db)
    since = datetime.utcnow() - timedelta(days=days)
    logs = (
        db.query(HealthLog)
        .filter(HealthLog.elder_id == elder_id, HealthLog.logged_at >= since)
        .order_by(desc(HealthLog.logged_at))
        .all()
    )
    return {"elder_id": elder_id, "days": days, "total_logs": len(logs), "logs": logs}


@router.get("/alerts/{elder_id}")
def get_alerts(
    elder_id: int,
    unresolved_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    elder = get_elder_or_404(elder_id, current_user, db)
    query = db.query(Alert).filter(Alert.elder_id == elder_id)
    if unresolved_only:
        query = query.filter(Alert.is_resolved == False)
    alerts = query.order_by(desc(Alert.triggered_at)).all()
    return {"elder_id": elder_id, "alerts": alerts}

@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    action_taken: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Verify the user actually owns the elder attached to this alert
    get_elder_or_404(alert.elder_id, current_user, db)

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.action_taken = action_taken
    db.commit()
    return {"status": "resolved", "alert_id": alert_id}


@router.get("/nearby-clinics/{elder_id}")
async def nearby_clinics(
    elder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    elder = get_elder_or_404(elder_id, current_user, db)
    if not elder.latitude or not elder.longitude:
        raise HTTPException(status_code=400, detail="Elder location not set")

    url = (
        f"https://api.geoapify.com/v2/places"
        f"?categories=healthcare.hospital"
        f"&filter=circle:{elder.longitude:.4f},{elder.latitude:.4f},10000"
        f"&limit=3&apiKey={GEOAPIFY_KEY}"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
    data = resp.json()

    clinics = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        clinics.append({
            "name": props.get("name", "Unknown"),
            "address": props.get("formatted", ""),
            "distance_m": props.get("distance", 0),
        })
    return {"elder_id": elder_id, "clinics": clinics}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import Elder
from pydantic import BaseModel

class ElderRegister(BaseModel):
    name: str
    age: int
    city: str
    phone: str = None

@router.post("/register", response_model=dict)
def register_elder(data: ElderRegister, db: Session = Depends(get_db)):
    # Check if phone already exists
    existing = db.query(Elder).filter(Elder.phone == data.phone).first()
    if existing:
        return {"status": "exists", "elder_id": existing.id}
    
    elder = Elder(
        caregiver_id=1,  # Default for testing
        name=data.name,
        age=data.age,
        city=data.city,
        phone=data.phone
    )
    db.add(elder)
    db.commit()
    db.refresh(elder)
    return {"status": "registered", "elder_id": elder.id}

from fastapi import Request, Form

# ... your existing routes ...

# 1. THE ROUTE HANDLER (The "Receiver")
@router.post("/whatsapp-webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(None),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None)
):
    # This part handles the incoming Twilio data
    message_text = Body or "No text provided"
    
    # CALL YOUR LOGIC HERE
    final_response = await get_ai_response(message_text)
    
    # Send the response back to Twilio
    response = MessagingResponse()
    response.message(final_response)
    return Response(content=str(response), media_type="application/xml")

# 2. THE LOGIC CHECKER (The "Processor" - keep this separate)
async def get_ai_response(text):
    # The Red Flag Shield
    emergency_keywords = ["chest pain", "breathing", "bleeding", "confusion", "unconscious", "cannot breathe"]
    
    if any(word in text.lower() for word in emergency_keywords):
        return "🚨 EMERGENCY ALERT: I detected keywords that may indicate a serious medical situation. Please stop using this app and call emergency services or your doctor immediately."

    # Proceed to AI analysis (You can add your Gemini call here later)
    # ai_result = analyze_with_gemini(text) 
    
    # The Disclaimer
    disclaimer = "\n\n(Note: This is a summary of your daily symptom log for your personal records. It is not medical advice. Do not make medical decisions based on this summary.)"
    
    return f"I have logged your update: '{text}' {disclaimer}"
    """Catches incoming WhatsApp messages and voice notes from Twilio"""
    
    print(f"Message received from: {From}")
    
    # Check if the user sent an audio file (voice note)
    if MediaUrl0 and "audio" in MediaContentType0:
        print(f"🎤 Voice note received! Audio URL: {MediaUrl0}")
        # Next steps: Download the audio, send to AI, update database
        reply_text = "Aarogya AI is analyzing your voice note..."
        
    # If they just typed a regular text message
    elif Body:
        print(f"💬 Text received: {Body}")
        reply_text = f"I received your message: {Body}. (Voice notes are preferred!)"
        
    else:
        reply_text = "I didn't understand that format. Please send a voice note."

    # Twilio requires an XML response to know the message was received
    response = MessagingResponse()
    response.message(reply_text)
    
    return Response(content=str(response), media_type="application/xml")