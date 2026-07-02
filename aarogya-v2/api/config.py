import os
import boto3
from supabase import create_client
from google import genai

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# Initialize NEW Gemini Client
gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
AAROGYA_MODEL = "gemini-2.5-flash"

# Initialize AWS S3
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "aarogya-voice-logs")

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name="ap-south-1" 
) if AWS_ACCESS_KEY and AWS_SECRET_KEY else None