import requests
import os
from app.schemas.workflow_agent import WorkflowState, ExecutionLogEntry
from app.tools.layout_generation_tool import generate_layout
from datetime import datetime, timezone

def design_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node representing the Design Agent.
    Takes terrain data and preferences, generates a 2D floor plan,
    and submits it to the ASP.NET Core internal API.
    """
    start_time = datetime.now(timezone.utc)
    
    # Extract inputs safely
    land_size = state.input_data.land_size_perches if state.input_data else 10.0
    preferences = state.input_data.preferences if state.input_data else {"bedrooms": 3, "floors": 2}
    
    terrain_type = "flat"
    if state.terrain_result and "terrain_type" in state.terrain_result:
        terrain_type = state.terrain_result["terrain_type"]
        
    # Generate layout using the rule-based templating tool
    design = generate_layout(land_size, terrain_type, preferences)
    state.design_result = design.model_dump()
    
    api_result = "success"
    
    # Call ASP.NET Core API to persist the design
    api_base_url = os.environ.get("ASPNET_API_URL", "https://localhost:7193/api/v1")
    try:
        # In a real environment with Docker Compose, this would be an internal service call
        # e.g. "http://api:8080/api/v1/internal/workflows/{id}/design"
        response = requests.post(
            f"{api_base_url}/internal/workflows/{state.workflow_id}/design",
            json=state.design_result,
            verify=False # Bypass SSL for local dev
        )
        if not response.ok:
            api_result = f"api_failed: {response.status_code}"
    except Exception as e:
        api_result = "api_call_skipped_local_dev" # For dev purposes if backend isn't up

    duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    state.execution_log.append(ExecutionLogEntry(
        agent_name="DesignAgent",
        action="Generated room layout and foundation",
        tool_called="layout_generation_tool",
        duration_ms=duration,
        result=api_result,
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))
    
    state.current_agent = "cost_estimation_agent"
    return state
