from fastapi import APIRouter, Security
from pydantic import BaseModel

from app.api.dependencies import verify_api_key

router = APIRouter()

class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 3
    category: str | None = None

@router.post("/knowledge/seed")
def seed_knowledge(api_key: str = Security(verify_api_key)):
    from app.knowledge.seeding_service import seed_knowledge_base
    stored, skipped = seed_knowledge_base()
    return {"stored": stored, "skipped": skipped}

@router.post("/knowledge/search")
def search_knowledge(
    request: KnowledgeSearchRequest,
    api_key: str = Security(verify_api_key)
):
    from app.knowledge.retrieval_service import search_knowledge_as_dicts
    results = search_knowledge_as_dicts(request.query, request.top_k, request.category)
    return {"results": results, "count": len(results)}
