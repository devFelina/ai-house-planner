from fastapi import APIRouter, Security
from pydantic import BaseModel

from app.api.dependencies import verify_api_key

router = APIRouter()

class MessageEntry(BaseModel):
    role: str
    content: str

class AssistantRequest(BaseModel):
    message: str
    history: list[MessageEntry] | None = None

@router.post("/assistant/interpret")
def interpret_message(
    request: AssistantRequest,
    api_key: str = Security(verify_api_key)
):
    from app.agents.architecture_assistant import interpret_user_message
    history_dicts = [m.model_dump() for m in request.history] if request.history else None
    return interpret_user_message(request.message, history=history_dicts)
