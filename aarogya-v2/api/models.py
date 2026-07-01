from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    city = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    elders = relationship("Elder", back_populates="caregiver")

class Elder(Base):
    __tablename__ = "elders"

    id = Column(Integer, primary_key=True, index=True)
    caregiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    city = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    known_conditions = Column(JSON, default=list)
    medications = Column(JSON, default=list)
    emergency_contact = Column(String(20), nullable=True)
    baseline_heart_rate = Column(Float, nullable=True)
    baseline_bp_systolic = Column(Float, nullable=True)
    baseline_bp_diastolic = Column(Float, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    chronic_conditions = Column(JSON, default=list)
    custom_triggers = Column(JSON, default=list)
    last_alert_sent = Column(DateTime(timezone=True), nullable=True)
    
    # This is the ONLY new line you need right now!
    preferred_language = Column(String, default="hindi") 

    caregiver = relationship("User", back_populates="elders")
    health_logs = relationship("HealthLog", back_populates="elder")
    alerts = relationship("Alert", back_populates="elder")
    
class HealthLog(Base):
    __tablename__ = "health_logs"

    id = Column(Integer, primary_key=True, index=True)
    elder_id = Column(Integer, ForeignKey("elders.id"))
    
    # Relationship to Elder
    elder = relationship("Elder", back_populates="health_logs")
    
    # Core AI Extracted Data
    transcript = Column(Text)
    symptoms = Column(JSON, default=list) 
    mood = Column(Integer, nullable=True) 
    audio_url = Column(String, nullable=True) 
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    log_date = Column(Date, nullable=True)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Optional / Legacy fields
    source = Column(String(20), default="manual")
    is_daily_summary = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    blood_pressure = Column(String(20), nullable=True)
    feeling_today = Column(String(50), nullable=True)
    appetite = Column(String(50), nullable=True)
    mobility = Column(String(50), nullable=True)
    had_fall = Column(Boolean, default=False)
    new_pain = Column(Boolean, default=False)
    new_pain_location = Column(String(100), nullable=True)
    blood_pressure_systolic = Column(Float, nullable=True)
    blood_pressure_diastolic = Column(Float, nullable=True)
    symptom_severity = Column(String(50), nullable=True)
    risk_level = Column(String(50), nullable=True)
    ai_recommendation = Column(String, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    elder_id = Column(Integer, ForeignKey("elders.id"), nullable=False)
    elder = relationship("Elder", back_populates="alerts")
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    action_taken = Column(Text, nullable=True)