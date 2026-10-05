"""
Land Analysis Agent — LangGraph node.

Analyzes a land photo using the vision classify tool and updates
the workflow state with terrain results. If no photo URL is available,
uses the manual terrain fallback from the coordinator.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.tools.vision_classification_tool import vision_classification_tool
from app.orchestration.tool_governance import (
    ToolAuthorizationError,
    assert_tool_allowed,
    mark_tool_authorization_failure,
)
from app.orchestration.tool_audit import (
    log_tool_failure,
    log_tool_success,
    start_tool_timer,
)


def _photo_url_for_state(state: WorkflowState) -> str | None:
    """Current workflow input has no photo URL; retain the existing fallback path."""
    return None


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
        # No photo URL in current deterministic input flow
        photo_url = _photo_url_for_state(state)

        if not photo_url:
            # No photo available — use safe default
            state.terrain_result = {
                "terrain_type": "flat",
                "slope_estimate": "flat",
                "notable_features": ["no_photo_provided", "defaulted_to_flat"]
            }
            action = "No photo URL available — defaulted to flat terrain"
        else:
            # Call the vision classification tool with retry logic
            try:
                assert_tool_allowed("land_analysis", "terrain_classifier")
            except ToolAuthorizationError as exc:
                return mark_tool_authorization_failure(
                    state, "LandAnalysisAgent", "terrain_classifier", exc
                )
            parsed_source = urlsplit(photo_url)
            tool_input = {
                "has_image": True,
                "source_type": "remote_url",
                "scheme": parsed_source.scheme.lower(),
                "query_present": bool(parsed_source.query),
            }
            started_at = start_tool_timer()
            success = False
            last_error = None
            for attempt in range(2): # 1 retry
                try:
                    terrain_result = vision_classification_tool(photo_url, workflow_id=state.workflow_id)
                    state.terrain_result = terrain_result.model_dump()
                    action = f"Classified terrain as '{terrain_result.terrain_type}' (slope: {terrain_result.slope_estimate})"
                    tool = "vision_classification_tool"
                    success = True
                    break
                except Exception as e:
                    last_error = e
                    print(f"[Land Analysis] Vision API failed on attempt {attempt+1}: {e}")

            if not success:
                log_tool_failure(
                    state=state,
                    agent_name="land_analysis",
                    tool_name="terrain_classifier",
                    started_at=started_at,
                    input_summary=tool_input,
                    error=last_error or RuntimeError("terrain classification failed"),
                )
                # Fallback to manual terrain
                manual_terrain = "flat"

                state.terrain_result = {
                    "terrain_type": manual_terrain,
                    "slope_estimate": "flat",
                    "notable_features": ["vision_failed_used_manual_fallback"]
                }
                action = f"Vision failed, fell back to flat terrain"
            else:
                log_tool_success(
                    state=state,
                    agent_name="land_analysis",
                    tool_name="terrain_classifier",
                    started_at=started_at,
                    input_summary=tool_input,
                    output_summary={
                        "terrain_type": terrain_result.terrain_type,
                        "slope_estimate": terrain_result.slope_estimate,
                        "notable_feature_count": len(terrain_result.notable_features),
                        "fallback_used": terrain_result.terrain_type == "unknown",
                    },
                )

    # Persist terrain result to ASP.NET (best-effort, don't block on failure)
    _persist_terrain(state)

    duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    state.execution_log.append(ExecutionLogEntry(
        agent_name="LandAnalysisAgent",
        action=action,
        tool_called=tool,
        duration_ms=duration,
        result="manual_terrain_required" if state.terrain_result.get("terrain_type") == "unknown" else "success",
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))

    return state


def _persist_terrain(state: WorkflowState):
    """Call ASP.NET internal API to save terrain results to the database."""
    if not state.terrain_result or not state.workflow_id:
        return

    try:
        headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
        payload = {
            "terrain_type": state.terrain_result.get("terrain_type", "unknown"),
            "slope_estimate": state.terrain_result.get("slope_estimate", "unknown"),
            "notable_features": state.terrain_result.get("notable_features", [])
        }
        response = requests.patch(
            f"{ASPNET_API_URL}/internal/workflows/{state.workflow_id}/terrain",
            json=payload,
            headers=headers,
            timeout=5,
        )
        if response.ok:
            print(f"[Land Analysis] Terrain persisted to database for workflow {state.workflow_id}")
        else:
            print(f"[Land Analysis] Failed to persist terrain: {response.status_code}")
    except requests.RequestException as e:
        print(f"[Land Analysis] Could not reach ASP.NET for terrain update: {e}")
