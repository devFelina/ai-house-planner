"""
Design Agent — LangGraph node.

Generates structured house layouts using deterministic templates and
submits them to ASP.NET Core for persistence. Supports both initial
generation and revision after validation failure.
"""
import requests
import os
from app.schemas.workflow_agent import WorkflowState, ExecutionLogEntry
from app.tools.layout_generation_tool import generate_layout
from app.tools.geometry_validator import validate_geometry
from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from datetime import datetime, timezone


def design_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node for house design generation.

    Flow:
    1. Extract inputs (land size, terrain, preferences)
    2. Check if this is a revision (validation_result with failures)
    3. Generate layout using template system
    4. Run geometry validation
    5. Submit to ASP.NET Core internal API for persistence
    """
    start_time = datetime.now(timezone.utc)

    # Extract inputs safely
    land_size = state.input_data.land_size_perches if state.input_data else 10.0
    preferences = state.input_data.preferences if state.input_data else {"bedrooms": 3, "floors": 2}

    terrain_type = "flat"
    if state.terrain_result and "terrain_type" in state.terrain_result:
        terrain_type = state.terrain_result["terrain_type"]

    # Check if this is a revision (validation failed on a previous design)
    previous_design = None
    revision_reason = None
    if state.validation_result and not state.validation_result.get("passed", True):
        previous_design = state.design_result
        revision_reason = state.validation_result.get("revision_reason", "Unknown validation failure")
        print(f"[Design Agent] Revision requested. Reason: {revision_reason}")

    # Generate layout using the template-based tool
    design = generate_layout(
        land_size_perches=land_size,
        terrain_type=terrain_type,
        preferences=preferences,
        previous_design=previous_design,
        revision_reason=revision_reason,
    )
    state.design_result = design.model_dump()

    # Run geometry validation locally before submitting
    validation = validate_geometry(
        rooms=design.rooms,
        expected_bedrooms=preferences.get("bedrooms", 3),
        expected_floors=preferences.get("floors", 2),
        land_size_perches=land_size,
    )

    if not validation.passed:
        print(f"[Design Agent] Local geometry validation warnings: {validation.failures}")
        # Still submit — the ASP.NET side and Member 4 validation will catch issues

    # Submit to ASP.NET Core for persistence
    api_result = _submit_design(state)

    duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    action = "Generated room layout and foundation"
    if revision_reason:
        action = f"Revised design — reason: {revision_reason[:100]}"

    state.execution_log.append(ExecutionLogEntry(
        agent_name="DesignAgent",
        action=action,
        tool_called="layout_generation_tool",
        duration_ms=duration,
        result=api_result,
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))

    state.current_agent = "cost_estimation"
    return state


def _submit_design(state: WorkflowState) -> str:
    """Submit the generated design to ASP.NET Core internal API."""
    try:
        headers = {
            "X-Internal-API-Key": INTERNAL_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{ASPNET_API_URL}/internal/workflows/{state.workflow_id}/design",
            json=state.design_result,
            headers=headers,
            timeout=10,
            verify=False  # Bypass SSL for local dev
        )
        if response.ok:
            result_data = response.json()
            print(f"[Design Agent] Design saved: version {result_data.get('version', '?')}, "
                  f"id {result_data.get('designId', '?')}")
            return "success"
        else:
            error_msg = f"api_failed: {response.status_code}"
            print(f"[Design Agent] API submission failed: {error_msg}")
            return error_msg
    except Exception as e:
        print(f"[Design Agent] Could not reach ASP.NET: {e}")
        return "api_call_skipped_local_dev"
