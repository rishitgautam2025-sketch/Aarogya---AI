from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

class OnboardingPayload(BaseModel):
    name: str
    age: int # Make this required
    phone: str
    city: str
    caregiver_phone: str
    chronic_conditions: List[str]
    custom_triggers: List[str]

@router.post("/api/onboarding")
async def register_new_patient(payload: OnboardingPayload):
    from api.main import supabase 
    
    try:
        # We use .insert() for new patients. 
        # Supabase will automatically assign the 'id' (serial)
        response = supabase.table("elders").insert({
            "name": payload.name,
            "age": payload.age,
            "phone": payload.phone,
            "caregiver_phone": payload.caregiver_phone,
            "city": payload.city,
            "chronic_conditions": payload.chronic_conditions,
            "custom_triggers": payload.custom_triggers,
            "caregiver_id": 1  # <--- Change this if your Supabase user ID is different!
        }).execute()
        
        # Check if the insert was successful
        # (Supabase .execute() returns data even on insert)
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create patient record.")
        
        return {"status": "success", "message": "Patient registered successfully."}

    except Exception as e:
        print(f"[ERROR] Registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))