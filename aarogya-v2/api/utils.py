import os
import requests
from api.config import supabase

def get_patient_context(sender_phone: str):
    """Looks up a patient record based on their WhatsApp number."""
    if supabase is None:
        return None
        
    clean_phone = sender_phone.strip()
    
    response = supabase.table("elders") \
        .select("*") \
        .eq("phone", clean_phone) \
        .single() \
        .execute()
    
    return response.data if response.data else None

def send_emergency_alert(patient_name: str, symptom: str, raw_message: str):
    """Sends a critical emergency email via Resend."""
    print("DEBUG: Entering send_emergency_alert function via Resend HTTP API...")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    RECEIVER_EMAIL = "rishitgautam8@gmail.com"

    if not RESEND_API_KEY:
        print("[ERROR] RESEND_API_KEY environment variable is missing!")
        return

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    email_body = f"""
    CRITICAL HEALTH ALERT
    Patient: {patient_name}
    Flagged Symptom: {symptom}
    Original Transcript: "{raw_message}"
    """

    payload = {
        "from": "Aarogya AI <onboarding@resend.dev>", 
        "to": [RECEIVER_EMAIL],
        "subject": f"URGENT: Aarogya AI Alert - {patient_name}",
        "text": email_body
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201, 202]:
            print("[SUCCESS] Emergency email dispatched securely via Resend!")
        else:
            print(f"[ERROR] Resend API rejected request: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Critical failure sending email: {e}")