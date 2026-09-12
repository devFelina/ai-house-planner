"""
Design Agent — LangGraph node.

Generates validated procedural house layouts and
submits them to ASP.NET Core for persistence. Supports both initial
generation and revision after validation failure.
"""
import requests
from app.schemas.workflow_agent import WorkflowState, ExecutionLogEntry
from app.tools.layout_generation_tool import generate_layout, prepare_inputs
from app.design.candidate_generator import GenerationFailure
from app.tools.geometry_validator import validate_geometry
from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from datetime import datetime, timezone


def design_node(state: WorkflowState) -> WorkflowState:
    """
    LangGraph node for house design generation.

    Flow:
    1. Extract inputs (land size, terrain, preferences)
    2. Check if this is a revision (validation_result with failures)
    3. Generate and rank eligible procedural layouts
    4. Run geometry validation
    5. Submit to ASP.NET Core internal API for persistence
    """
    start_time = datetime.now(timezone.utc)

    # Extract inputs safely
    land_size = state.input_data.land_size_perches if state.input_data else 10.0
    preferences = state.input_data.preferences if state.input_data else {"bedrooms": 3, "floors": 2}

    terrain_type = "unknown"
    if state.terrain_result and "terrain_type" in state.terrain_result:
        terrain_type = state.terrain_result["terrain_type"]

    # Check if this is a revision (validation failed on a previous design)
    previous_design = None
    revision_reason = None
    if state.validation_result and not state.validation_result.get("passed", True):
        previous_design = state.design_result
        revision_reason = state.validation_result.get("revision_reason", "Unknown validation failure")
        print(f"[Design Agent] Revision requested. Reason: {revision_reason}")

    # Soft vision observations may inform concepts, never structural calculations.
    preferences = dict(preferences)
    preferences['notable_features'] = (state.terrain_result or {}).get('notable_features', [])
    try:
        plot_input = state.input_data.plot_constraints if state.input_data else None
        seed = state.input_data.design_seed if state.input_data else None
        design = generate_layout(
            land_size_perches=land_size, terrain_type=terrain_type,
            preferences=preferences, previous_design=previous_design,
            revision_reason=revision_reason, plot_constraints=plot_input, design_seed=seed,
        )
        req, plot = prepare_inputs(land_size, terrain_type, preferences, plot_input, seed)
        validation = validate_geometry(design.rooms, req.bedrooms, req.floors, land_size,
                                       plot=plot, design=design)
        if not validation.passed:
            raise GenerationFailure('Local geometry validation failed.', [{'failures': validation.failures}])
    except (GenerationFailure, ValueError) as exc:
        state.design_result = None
        state.status = 'failed'
        state.current_agent = 'failed'
        state.approval_status = 'not_requested'
        state.validation_result = {'passed': False, 'failures': [str(exc)],
                                   'candidate_failures': getattr(exc, 'failures', [])}
        state.execution_log.append(ExecutionLogEntry(
            agent_name='DesignAgent', action='Design generation failed; no layout submitted',
            tool_called='layout_generation_tool', result=str(exc),
            created_at_utc=datetime.now(timezone.utc).isoformat()))
        _persist_failure(state)
        return state
    state.design_result = design.model_dump()
    state.validation_result = validation.to_dict()

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


def _persist_failure(state: WorkflowState) -> None:
    """Expose safe failure through the existing gateway polling workflow."""
    try:
        response = requests.patch(
            f'{ASPNET_API_URL}/internal/workflows/{state.workflow_id}/status',
            json={'status': 'failed'}, headers={'X-Internal-API-Key': INTERNAL_API_KEY},
            timeout=5, verify=False)
        response.raise_for_status()
    except requests.RequestException as exc:
        state.execution_log.append(ExecutionLogEntry(
            agent_name='DesignAgent', action='Could not persist failed workflow status',
            result=type(exc).__name__, created_at_utc=datetime.now(timezone.utc).isoformat()))
