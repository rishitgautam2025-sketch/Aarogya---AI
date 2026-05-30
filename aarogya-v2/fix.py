from api.database import SessionLocal
from api.models import Elder

db = SessionLocal()

# Grab Prachi (Elder #1)
elder = db.query(Elder).filter(Elder.id == 1).first()

if elder:
    print(f"Old number was: '{elder.phone}'")
    
    # FORMAT: "+91" followed by your 10 digits. NO SPACES.
    # Replace 9876543210 with your actual WhatsApp number
    elder.phone = "+918287651315" 
    
    db.commit()
    print(f"✅ Number successfully updated to: '{elder.phone}'")
else:
    print("Elder not found.")

db.close()