"""
Land Analysis Agent — LangGraph node.

Analyzes a land photo using the vision classify tool and updates
the workflow state with terrain results. If no photo URL is available,
uses the manual terrain fallback from the coordinator.
"""
import requests
from app.schemas.workflow_state import WorkflowState, ExecutionLogEntry
from app.tools.vision_classify_tool import vision_classify_tool
from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from datetime import datetime, timezone


def land_analysis_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node for terrain classification.

    Flow:
    1. Check if manual terrain was already set by coordinator → skip vision
    2. Extract photo_url from input_data preferences
    3. Call vision tool → get TerrainResult
    4. Validate and persist to workflow state
    5. Call ASP.NET internal API to update terrain on WorkflowState
    """
    start_time = datetime.now(timezone.utc)
    tool = None

    # If terrain already filled by coordinator (manual fallback), just pass through
    if state.terrain_result and state.terrain_result.get("terrain_type"):
        action = f"Skipped vision — manual terrain '{state.terrain_result['terrain_type']}' already set"
    else:
        # Extract photo URL from preferences
        photo_url = None
        if state.input_data and state.input_data.preferences:
            photo_url = state.input_data.preferences.get("photo_url")

        if not photo_url:
            # No photo available — use safe default
            state.terrain_result = {
                "terrain_type": "flat",
                "slope_estimate": "unknown",
                "notable_features": ["no_photo_provided"]
            }
            action = "No photo URL available — defaulted to flat terrain"
        else:
            # Call the vision classification tool
            terrain_result = vision_classify_tool(photo_url)
            state.terrain_result = terrain_result.model_dump()
            action = f"Classified terrain as '{terrain_result.terrain_type}' (slope: {terrain_result.slope_estimate})"
            tool = "vision_classify_tool"

    # Persist terrain result to ASP.NET (best-effort, don't block on failure)
    _persist_terrain(state)

    duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    state.execution_log.append(ExecutionLogEntry(
        agent_name="LandAnalysisAgent",
        action=action,
        tool_called=tool,
        duration_ms=duration,
        result="success",
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))

    state.current_agent = "design"
    return state


def _persist_terrain(state: WorkflowState):
    """Call ASP.NET internal API to save terrain results to the database."""
    if not state.terrain_result or not state.workflow_id:
        return

    try:
        headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
        payload = {
            "terrain_type": state.terrain_result.get("terrain_type", "flat"),
            "slope_estimate": state.terrain_result.get("slope_estimate", "unknown"),
            "notable_features": state.terrain_result.get("notable_features", [])
        }
        response = requests.patch(
            f"{ASPNET_API_URL}/internal/workflows/{state.workflow_id}/terrain",
            json=payload,
            headers=headers,
            timeout=5,
            verify=False  # Local dev SSL bypass
        )
        if response.ok:
            print(f"[Land Analysis] Terrain persisted to database for workflow {state.workflow_id}")
        else:
            print(f"[Land Analysis] Failed to persist terrain: {response.status_code}")
    except Exception as e:
        print(f"[Land Analysis] Could not reach ASP.NET for terrain update: {e}")