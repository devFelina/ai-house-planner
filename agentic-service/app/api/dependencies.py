import secrets
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import INTERNAL_API_KEY

api_key_header = APIKeyHeader(name="X-Internal-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if not secrets.compare_digest(api_key, INTERNAL_API_KEY):
        raise HTTPException(status_code=403, detail="Forbidden:Invalid API Key")
    return api_key
