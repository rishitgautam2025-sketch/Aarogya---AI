from api.database import SessionLocal
import api.models

db = SessionLocal()

# 1. Create a dummy caregiver
caregiver = api.models.User(name="Admin", email="admin@test.com", password_hash="hash")
db.add(caregiver)
db.commit()

# 2. Create Elder #1 (This fixes the 404!)
elder = api.models.Elder(
    name="Prachi", 
    age=45, 
    city="Pune", 
    phone="+918287651315", # PUT YOUR WHATSAPP NUMBER HERE
    caregiver_id=caregiver.id
)
db.add(elder)
db.commit()

print("✅ Success! Elder #1 created.")
db.close()