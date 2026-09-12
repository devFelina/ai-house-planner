from fastapi import FastAPI, HTTPException, Security, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel 
from uuid import UUID, uuid4
from typing import Optional, Dict, Any

from app.schemas.workflow_state import WorkflowState, CoordinatorInput
from app.workflows.house_planning_graph import app_graph

app = FastAPI(title="Agentic AI Service - House Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # Allow React app explicitly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Internal auth mechanism where ASP.NET can call this API
api_key_header=APIKeyHeader(name="X-Internal-API-Key")

def verify_api_key(api_key: str=Security(api_key_header)):
    if api_key!="shared-internal-secret":
        raise HTTPException(status_code=403,detail="Forbidden:Invalid API Key")
    return api_key

class StartWorkflowRequest(BaseModel):
    workflow_id: UUID
    submission_id: UUID
    budget_lkr: Optional[float] = None
    land_size_perches: float
    manual_terrain_type: Optional[str] = None
    preferences: Dict[str, Any]
    plot_constraints: Optional[Dict[str, Any]] = None
    design_seed: Optional[int] = None

class ResumeWorkflowRequest(BaseModel):
    workflow_id: UUID
    resume_from: str
    user_revision_prompt: str
    budget_lkr: Optional[float] = None
    land_size_perches: float
    manual_terrain_type: Optional[str] = None
    preferences: Dict[str, Any]
    terrain_result: Optional[Dict[str, Any]] = None
    previous_design: Optional[str] = None

def execute_workflow(initial_state:WorkflowState):
    """Background task to run the LangGraph workflow"""
    print(f"Starting workflow execution for {initial_state.workflow_id}")
    app_graph.invoke(initial_state)

@app.post("/workflows/start")
def start_workflow(
    request:StartWorkflowRequest,
    background_tasks:BackgroundTasks,
    api_key:str=Security(verify_api_key)
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
    background_tasks.add_task(execute_workflow,initial_state)

    return{
        "message":"Workflow started successfully",
        "workflow_id":str(request.workflow_id)
    }

@app.post("/workflows/resume")
def resume_workflow(
    request: ResumeWorkflowRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Security(verify_api_key)
):
    import json
    
    # Reconstruct input data
    input_data = CoordinatorInput(
        submission_id=request.workflow_id,
        budget_lkr=request.budget_lkr,
        land_size_perches=request.land_size_perches,
        manual_terrain_type=request.manual_terrain_type,
        preferences=request.preferences,
    )
    
    previous_design_obj = None
    if request.previous_design:
        try:
            previous_design_obj = json.loads(request.previous_design)
        except:
            pass

    state = WorkflowState(
        workflow_id=request.workflow_id,
        status="running",
        current_agent=request.resume_from, # Set the router to start here
        input_data=input_data,
        terrain_result=request.terrain_result,
        design_result=previous_design_obj,
        validation_result={"passed": False, "revision_reason": request.user_revision_prompt}
    )
    
    background_tasks.add_task(execute_workflow, state)
    return {"message": "Workflow resumed successfully", "workflow_id": str(request.workflow_id)}

