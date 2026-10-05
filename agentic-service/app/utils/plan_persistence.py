import os
import json
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
from app.schemas.workflow_state import WorkflowState
from app.schemas.workflow_plan import WorkflowPlan

from app.config import ASPNET_API_URL, INTERNAL_API_KEY

class PlanPersistenceError(Exception):
    """Raised when the workflow plan cannot be durably persisted."""
    pass

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
def _do_persist_plan(workflow_id: str, payload: dict) -> None:
    endpoint = f"{ASPNET_API_URL.strip().rstrip('/')}/internal/workflows/{workflow_id}/plan"
    headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
    
    with httpx.Client(timeout=10.0) as client:
        response = client.patch(endpoint, json=payload, headers=headers)
        response.raise_for_status()

def persist_workflow_plan_state(state: WorkflowState) -> None:
    if state.plan is None:
        return
        
    # Serialize plan using model_dump to handle enums and nested objects cleanly
    plan_data = state.plan.model_dump(mode="json")
    
    payload = {
        "plan": plan_data,
        "currentStepId": state.current_step_id,
        "completedStepIds": state.completed_step_ids
    }
    
    try:
        _do_persist_plan(str(state.workflow_id), payload)
    except Exception as e:
        raise PlanPersistenceError(f"Failed to durably persist workflow plan after retries: {e}") from e
