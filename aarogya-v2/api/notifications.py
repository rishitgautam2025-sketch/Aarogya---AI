import os
from datetime import datetime, timezone
from twilio.rest import Client

def trigger_emergency_call(to_phone: str, patient_name: str, symptom_label: str, reasoning: str):
    """
    Triggers a live outbound phone call to the caregiver and reads the emergency alert details.
    """
    # Use a generic name (a Key) inside the parentheses
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    if not all([account_sid, auth_token, from_number]):
        print("[ERROR] Twilio credentials missing from environment variables.")
        return None

    client = Client(account_sid, auth_token)

    # Clean up strings for text-to-speech synthesis
    speech_text = (
        f"Urgent alert from Aarogya A.I. Patient {patient_name} has reported a critical symptom: "
        f"{symptom_label}. Reason for escalation: {reasoning}. Please log into your dashboard immediately."
    )

    # TwiML payload using the clear, standard 'alice' voice
    twiml_xml = f"""
    <Response>
        <Pause length="1"/>
        <Say voice="alice" language="en-IN" loop="2">{speech_text}</Say>
    </Response>
    """

    try:
        call = client.calls.create(
            twiml=twiml_xml,
            to=to_phone,
            from_=from_number
        )
        print(f"[SUCCESS] Outbound call initialized. SID: {call.sid}")
        return call.sid
    except Exception as e:
        print(f"[ERROR] Twilio call failed to dispatch: {e}")
        return None