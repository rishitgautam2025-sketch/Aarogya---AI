"""
Elder Monitor Router — SECURED with JWT auth + anomaly detection + Supabase Storage.
"""

import os
import io
import json
import httpx
import requests
from datetime import datetime, timedelta
from typing import Optional, List

import openai
import google.generativeai as genai
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

from fastapi import APIRouter, Request, Depends, Form, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from api.database import get_db
from api.models import Elder, User, HealthLog, Alert
from api.auth import get_current_active_user, get_current_user
from api.routers.whatsapp import send_whatsapp
from api.storage import upload_audio

load_dotenv()

# Setup AI
openai.api_key = os.getenv("OPENAI_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
GEOAPIFY_KEY = os.getenv("GEOAPIFY_KEY", "c7c39837c677431cb5568b46a9e4f6a7")

router = APIRouter(prefix="/elder-monitor", tags=["Elder Monitor"])

# ── Pydantic schemas ──────────────────────────────────────────────

class ElderCreate(BaseModel):
    name: str
    age: int
    city: str
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    known_conditions: Optional[List[str]] = []
    medications: Optional[List[str]] = []
    emergency_contact: Optional[str] = None

class HealthLogCreate(BaseModel):
    elder_id: int
    feeling_today: Optional[str] = None
    appetite: Optional[str] = None
    mobility: Optional[str] = None
    had_fall: Optional[bool] = False
    new_pain: Optional[bool] = False
    new_pain_location: Optional[str] = None
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[float] = None
    blood_pressure_diastolic: Optional[float] = None
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
    """Returns: (is_anomaly, severity, message)"""
    warnings = []
    severity = "YELLOW"

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
    if log.temperature:
        if log.temperature > 38.5:
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
    return db.query(Elder).filter(Elder.caregiver_id == current_user.id).all()

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
    elder = db.query(Elder).filter(Elder.id == payload.elder_id).first()
    if not elder:
        raise HTTPException(status_code=404, detail="Patient not found")

    is_anomaly, severity, message = detect_anomaly(payload)

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
    
    if elder and elder.phone:
        risk = getattr(new_log, 'risk_level', 'normal').lower()

        if risk in ["moderate", "medium", "borderline", "elevated", "yellow"]:
            alert_message = f"🟡 Aarogya AI Notice: Vitals for {elder.name} are slightly abnormal (Temp: {new_log.temperature}°C). Can you please double-check their vitals and log them again to be safe?"
            try:
                send_whatsapp(to=elder.phone, message=alert_message)
            except Exception as e:
                print(f"Failed to trigger WhatsApp: {e}")
        
        elif risk == "high" or is_anomaly:
            alert_message = f"🚨 Aarogya AI Alert: HIGH RISK detected for {elder.name}. Issue: {new_log.ai_recommendation}"
            try:
                send_whatsapp(to=elder.phone, message=alert_message)
            except Exception as e:
                print(f"Failed to trigger WhatsApp: {e}")
        
    alert_data = None
    if is_anomaly:
        new_alert = Alert(
            elder_id=payload.elder_id,
            alert_type="MEDICAL_ANOMALY", 
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


# ── THE NEW WHATSAPP WEBHOOK ──────────────────────────────────────

@router.post("/whatsapp-webhook")
async def whatsapp_webhook(
    db: Session = Depends(get_db),
    From: str = Form(...),
    Body: str = Form(None),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None),
    MediaSid0: str = Form(None),
):
    from_num = From.replace("whatsapp:", "").strip()
    message_text = Body or ""
    audio_public_url = None

    # ── 1. AUDIO HANDLING ──
    if MediaUrl0 and MediaContentType0 and "audio" in MediaContentType0:

        # Download from Twilio
        r = requests.get(
            MediaUrl0,
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_TOKEN)
        )
        audio_bytes = r.content

        # Upload to Supabase Storage
        audio_public_url = upload_audio(audio_bytes)

        # Transcribe with Whisper — pure memory
        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.name = "voice_note.ogg"

        openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_buffer,
        )
        message_text = transcript.text

        if MediaSid0:
            try:
                Client(TWILIO_SID, TWILIO_TOKEN)\
                    .api.v2010.account(TWILIO_SID)\
                    .media(MediaSid0).delete()
            except Exception as e:
                print(f"[WARN] Could not delete Twilio media: {e}")

    # ── 2. EMERGENCY SHIELD ──
    emergency_keywords = [
        "chest pain", "saans", "breathless",
        "bleeding", "emergency", "cannot breathe", "unconscious"
    ]
    if any(word in message_text.lower() for word in emergency_keywords):
        twiml = MessagingResponse()
        twiml.message(
            "🚨 EMERGENCY ALERT: Serious symptoms detected. "
            "Please call emergency services or go to your nearest hospital immediately."
        )
        return Response(content=str(twiml), media_type="application/xml")

    # ── 3. AI ANALYSIS ──
    ai_summary = "No message content to analyze."
    if message_text:
        try:
            gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = (
                f"A patient sent this health update: '{message_text}'. "
                "Extract any symptoms mentioned and provide a brief 1-2 sentence "
                "clinical summary. Be concise and factual."
            )
            ai_summary = gemini_model.generate_content(prompt).text
        except Exception as e:
            print(f"[WARN] Gemini analysis failed: {e}")
            ai_summary = "AI analysis unavailable. Log saved."

    # ── 4. SAVE TO DATABASE ──
    elder = db.query(Elder).filter(Elder.phone == from_num).first()

    if elder:
        new_log = HealthLog(
            elder_id=elder.id,
            notes=message_text,
            ai_recommendation=ai_summary,
            audio_url=audio_public_url,
            risk_level="GREEN",
            logged_at=datetime.utcnow(),
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        print(f"[INFO] Log saved for elder {elder.name}, log_id={new_log.id}")
    else:
        print(f"[WARN] No elder found with phone={from_num}. Log not saved.")

    # ── 5. REPLY TO WHATSAPP ──
    disclaimer = (
        "\n\n(Note: This is a summary of your symptom log. "
        "It is not medical advice.)"
    )
    reply = f"✅ Aarogya AI received your update:\n{ai_summary}{disclaimer}"

    twiml = MessagingResponse()
    twiml.message(reply)
    return Response(content=str(twiml), media_type="application/xml")