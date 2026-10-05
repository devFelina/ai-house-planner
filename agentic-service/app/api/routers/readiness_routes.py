from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Security
from pydantic import BaseModel

from app.api.dependencies import verify_api_key
from app.workflows.procurement_graph import run_readiness_workflow

router = APIRouter(prefix="/api/v1/orchestration", tags=["Orchestration"])

class ConstructionPhase(BaseModel):
    phase_id: UUID
    name: str
    order: int
    status: str
    start_date: str | None = None
    end_date: str | None = None

class MaterialInventory(BaseModel):
    id: UUID
    phase_id: UUID | None = None
    name: str
    required: float
    available: float
    ordered: float
    unit: str

class ReadinessRequest(BaseModel):
    project_id: UUID
    project_data: dict[str, Any]
    construction_plan: List[ConstructionPhase]
    inventory: List[MaterialInventory]

@router.post("/readiness")
async def generate_readiness_plan(
    request: ReadinessRequest,
    api_key: str = Security(verify_api_key)
):
    from fastapi import HTTPException
    import traceback
    
    # Convert Pydantic request to dictionary for LangGraph state
    input_state = {
        "project_id": str(request.project_id),
        "project_data": request.project_data,
        "construction_plan": [phase.model_dump(mode='json') for phase in request.construction_plan],
        "inventory": [item.model_dump(mode='json') for item in request.inventory],
        "required_materials": [],
        "available_materials": [],
        "shortages": [],
        "procurement_plan": [],
        "risks": [],
        "acceleration_opportunities": [],
        "final_recommendation": {}
    }

    try:
        result = run_readiness_workflow(input_state)
        return result
    except Exception as e:
        error_msg = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}\n{error_msg}")
