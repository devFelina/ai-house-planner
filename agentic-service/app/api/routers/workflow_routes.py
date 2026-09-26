from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Security
from pydantic import BaseModel

from app.api.dependencies import verify_api_key
from app.design.generation.revision import preserve_revision_preferences
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.workflows.house_planning_graph import app_graph

router = APIRouter()

class StartWorkflowRequest(BaseModel):
    workflow_id: UUID
    submission_id: UUID
    land_size_perches: float
    budget_lkr: float | None = None
    manual_terrain_type: str | None = None
    preferences: dict[str, Any]
    plot_constraints: dict[str, Any] | None = None
    design_seed: int | None = None
    preferred_plan_code: str | None = None

class ResumeWorkflowRequest(BaseModel):
    workflow_id: UUID
    resume_from: str
    user_revision_prompt: str
    land_size_perches: float
    budget_lkr: float | None = None
    manual_terrain_type: str | None = None
    preferences: dict[str, Any]
    terrain_result: dict[str, Any] | None = None
    previous_design: dict[str, Any] | None = None
    plot_constraints: dict[str, Any] | None = None
    design_seed: int | None = None
    regeneration: bool = False
    previous_base_plan_code: str | None = None
    previous_design_fingerprint: str | None = None

def execute_workflow(initial_state: WorkflowState):
    """Background task to run the LangGraph workflow"""
    print(f"Starting workflow execution for {initial_state.workflow_id}")
    app_graph.invoke(initial_state)

@router.post("/workflows/start")
def start_workflow(
    request: StartWorkflowRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    """
    Endpoint called by ASP.NET Core component after a successful intake
    """
    #Construct initial state
    initial_state=WorkflowState(
        workflow_id=request.workflow_id,
        status="running",
        input_data=CoordinatorInput(**request.model_dump())
    )

    #To make the LangGraph response quicker it is passed to a background task so the API responds to ASP.NET Core immediately
    background_tasks.add_task(execute_workflow, initial_state)

    return{
        "message":"Workflow started successfully",
        "workflow_id":str(request.workflow_id)
    }

@router.post("/workflows/resume")
def resume_workflow(
    request: ResumeWorkflowRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    if request.resume_from != "design":
        raise HTTPException(status_code=400, detail="Only design revisions are supported")
    try:
        preferences = preserve_revision_preferences(request.preferences, request.previous_design)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Reconstruct input data
    input_data = CoordinatorInput(
        submission_id=request.workflow_id,
        land_size_perches=request.land_size_perches,
        budget_lkr=request.budget_lkr,
        manual_terrain_type=request.manual_terrain_type,
        preferences=preferences,
        plot_constraints=request.plot_constraints,
        design_seed=request.design_seed,
        regeneration=request.regeneration,
        previous_base_plan_code=request.previous_base_plan_code,
        previous_design_fingerprint=request.previous_design_fingerprint,
    )
    state = WorkflowState(
        workflow_id=request.workflow_id,
        status="running",
        current_agent=request.resume_from, # Set the router to start here
        input_data=input_data,
        terrain_result=request.terrain_result,
        design_result=request.previous_design,
        validation_result={"passed": False, "revision_reason": request.user_revision_prompt},
        user_revision_prompt=request.user_revision_prompt,
        approval_status="revision_requested",
    )
    
    background_tasks.add_task(execute_workflow, state)
    return {"message": "Workflow resumed successfully", "workflow_id": str(request.workflow_id)}
