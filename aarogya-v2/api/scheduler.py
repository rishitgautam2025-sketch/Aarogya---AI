from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, timedelta
from api.database import SessionLocal
from api.models import Elder, HealthLog
# Adjust this import to match wherever your send_whatsapp function lives!
from api.routers.whatsapp import send_whatsapp 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def morning_ping():
    db = next(get_db())
    yesterday = date.today() - timedelta(days=1)
    
    elders = db.query(Elder).all()
    for elder in elders:
        log = db.query(HealthLog).filter(
            HealthLog.elder_id == elder.id, 
            HealthLog.created_at >= yesterday 
        ).first()
        
        # If they had symptoms yesterday, check on them dynamically!
        if log and log.mood <= 2:
            # Safely get the symptoms (handles if it's a list or a string)
            if isinstance(log.symptoms, list):
                symptoms_text = ", ".join(log.symptoms)
            else:
                symptoms_text = log.symptoms or "takleef"

            custom_message = f"Good morning {elder.name}! Kal aapne {symptoms_text} ke baare mein bataya tha. Kya aaj thoda aaram hai? Dawai time pe le lijiye."
            
            send_whatsapp(elder.phone, custom_message)
            print(f"Personalized morning ping sent to {elder.name}")

def afternoon_ping():
    db = next(get_db())
    yesterday = date.today() - timedelta(days=1)
    
    elders = db.query(Elder).all()
    for elder in elders:
        log = db.query(HealthLog).filter(
            HealthLog.elder_id == elder.id, 
            HealthLog.created_at >= yesterday
        ).first()
        
        if log and log.mood <= 2:
            if isinstance(log.symptoms, list):
                symptoms_text = ", ".join(log.symptoms)
            else:
                symptoms_text = log.symptoms or "takleef"
                
            custom_message = f"Namaste {elder.name}, dopahar ka check-in! Aapka {symptoms_text} kaisa hai abhi? Khana kha ke aaram kijiye."
            
            send_whatsapp(elder.phone, custom_message)
            print(f"Personalized afternoon ping sent to {elder.name}")

def evening_ping():
    db = next(get_db())
    today = date.today()
    
    elders = db.query(Elder).all()
    for elder in elders:
        log_today = db.query(HealthLog).filter(
            HealthLog.elder_id == elder.id, 
            HealthLog.created_at >= today
        ).first()
        
        # If they haven't sent a voice note today, prompt them
        if not log_today:
            send_whatsapp(elder.phone, f"Namaste {elder.name}! Aaj ka din kaisa raha? Mujhe ek chhota sa voice note bhej dijiye.")
            print(f"Evening summary ping sent to {elder.name}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # Scheduled for 9 AM, 2 PM, and 6 PM
    scheduler.add_job(morning_ping, 'cron', hour=9, minute=0)
    scheduler.add_job(afternoon_ping, 'cron', hour=14, minute=0)
    scheduler.add_job(evening_ping, 'cron', hour=18, minute=0)
    
    scheduler.start()
    print("⏰ Aarogya AI Scheduler engine started! Smart pings are active.")