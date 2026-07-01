from fastapi import APIRouter
from datetime import datetime, timedelta

router = APIRouter()

@router.post("/api/generate-monthly-report/{elder_id}")
async def generate_monthly_report(elder_id: str):
    # THE FIX: We moved the import INSIDE the function to break the circular loop!
    from api.main import supabase, gemini_model, send_email 

    # 1. Fetch logs from the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    logs = supabase.table("voice_logs") \
        .select("*") \
        .eq("patient_id", elder_id) \
        .gte("created_at", thirty_days_ago.isoformat()) \
        .execute()

    if not logs.data:
        return {"status": "No logs found for this period"}

    # 2. Compile content for AI
    raw_history = "\n".join([f"Date: {log['created_at']}, Text: {log['raw_text']}" for log in logs.data])

    # 3. AI Summary Prompt
    prompt = f"""You are a professional medical scribe. 
    Analyze the following patient voice logs from the last 30 days:
    {raw_history}
    
    Provide a structured summary for the patient's doctor:
    1. Key Symptoms Reported (Frequency & Trend).
    2. Any Worsening Conditions.
    3. General Sentiment/Wellbeing notes.
    
    Crucial: Do not provide a diagnosis. Keep it objective, factual, and strictly based on the logs."""
    
    report = gemini_model.generate_content(prompt).text
    
    # 4. Email the report (using Resend)
    send_email(
        to="caretaker@example.com",
        subject=f"Aarogya AI: Monthly Health Report for Patient {elder_id}",
        body=report
    )
    
    return {"status": "Report sent successfully"}