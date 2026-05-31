# api/storage.py
import os
import uuid
from supabase import create_client, Client

_client: Client = None

def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _client = create_client(url, key)
    return _client

BUCKET = "audio-messages"

def upload_audio(file_bytes: bytes) -> str:
    """
    Uploads an .ogg audio file to Supabase Storage.
    Returns the public URL string to store in your database.
    """
    client = _get_client()
    filename = f"whatsapp/{uuid.uuid4()}.ogg"

    client.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": "audio/ogg", "upsert": "false"}
    )

    return client.storage.from_(BUCKET).get_public_url(filename)