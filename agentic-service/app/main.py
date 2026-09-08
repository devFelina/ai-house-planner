from fastapi import FASTAPI,HTTPException,Security,BackgroundTasks
from fastapi.security import APIKeyHeader
from pydantic import BaseModel 
from uuid import UUID,uuid4
from typing import Optional,Dict,Any

from app.schemas.workflow_state import WorkflowState, CoordinatorInput
from app.workflows.house_planning_graph import app_graph

app=FASTAPI(title="Agentic AI Service - House Planner")

#Internal auth mechanism where ASP.NET can call this API
api_key_header=APIKeyHeader(name="X-Internal-API-Key")

def verify_api_key(api_key: str=Security(api_key_header)):
    if api_key!="shared-internal-secret":
        raise HTTPException(status_code=403,detail="Forbidden:Invalid API Key")
    return api_key

class StartWorkflowRequest(BaseModel):
    submission_id:UUID
    budget_lkr:float
    land_size_perches:float
    manual_terrain_type:Optional[str]=None
    preferences:Dict[str,Any]

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
    workflow_id=uuid4()

    #Construct initial state
    initial_state=WorkflowState(
        workflow_id=workflow_id,
        status="running",
        input_data=CoordinatorInput(**request.model_dump())
    )

    #To make the LangGraph response quicker it is passed to a background task so the API responds to ASP.NET Core immediately
    background_tasks.add_task(execute_workflow,initial_state)

    return{
        "message":"Workflow started successfully",
        "workflow_id":str(workflow_id)
    }

