from app.schemas.workflow_agent import WorkflowState, ExecutionLogEntry
from app.tools.vision_classify_tool import vision_classify_tool
from datetime import datetime, timezone

def land_analysis_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node representing the Land Analysis Agent.
    It takes a land photo URL, analyzes it using the vision tool,
    and updates the state with the terrain results.
    """
    start_time = datetime.now(timezone.utc)
    
    # Check if manual terrain was provided as fallback
    if state.input_data and state.input_data.manual_terrain_type:
        state.terrain_result = {
            "terrain_type": state.input_data.manual_terrain_type,
            "slope_estimate": "unknown",
            "notable_features": []
        }
        action = "Skipped vision, used manual terrain"
        tool = None
    else:
        # We would pass the actual photo URL from state.input_data here
        # Mocking the call for now
        terrain_result = vision_classify_tool("http://blob-storage/photo.jpg")
        state.terrain_result = terrain_result.model_dump()
        action = "Extracted terrain from photo"
        tool = "vision_classify_tool"

    duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
    
    state.execution_log.append(ExecutionLogEntry(
        agent_name="LandAnalysisAgent",
        action=action,
        tool_called=tool,
        duration_ms=duration,
        result="success",
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))
    
    state.current_agent = "design_agent"
    return state
