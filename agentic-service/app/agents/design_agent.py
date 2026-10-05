"""
Design Agent — LangGraph node.

Generates validated procedural house layouts and
submits them to ASP.NET Core for persistence. Supports both initial
generation and revision after validation failure.
"""
from datetime import datetime, timezone

import requests

from app.config import ASPNET_API_URL, INTERNAL_API_KEY
from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.exceptions import GenerationFailure
from app.design.generation.revision import preserve_revision_preferences
from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.validation.geometry_validator import validate_geometry
from app.design.generation.generation_service import generate_layout, prepare_inputs
from app.design.visualization import VisualizationAgent
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

    if state.ai_design_generated and state.design_result and state.design_version is not None:
        print("[AI DESIGN] Existing design reused")
        return state

    # Extract inputs safely
    land_size = state.input_data.land_size_perches if state.input_data else 10.0
    
    terrain_type = "flat"

    # Check if this is a revision (validation failed on a previous design)
    previous_design = None
    revision_reason = None
    if state.validation_result and not state.validation_result.get("passed", True):
        previous_design = state.design_result
        errors = state.validation_result.get("errors") or state.validation_result.get("failures") or []
        revision_reason = state.validation_result.get("revision_reason") or ("; ".join(errors) if errors else state.validation_result.get("reason", "Unknown validation failure"))
        print(f"[Design Agent] Revision requested. Reason: {revision_reason}")
    if state.user_revision_prompt:
        previous_design = state.design_result
        revision_reason = state.user_revision_prompt
        print(f"[Design Agent] Human revision request received: {revision_reason}")

    # Build preferences strictly from CoordinatorInput for backward-compatibility with prepare_inputs
    preferences = {
        "bedrooms": getattr(state.input_data, 'bedrooms', 3) if state.input_data else 3,
        "bathrooms": getattr(state.input_data, 'bathrooms', 2) if state.input_data else 2,
        "style": getattr(state.input_data, 'house_type', 'conventional') if state.input_data else 'conventional',
        "floors": 1,
        "notable_features": (state.terrain_result or {}).get('notable_features', [])
    }
    tool_input = {
        "bedrooms": preferences["bedrooms"],
        "bathrooms": preferences["bathrooms"],
        "floors": preferences["floors"],
        "land_size_perches": land_size,
        "terrain_type": terrain_type,
        "seed_present": bool(state.input_data and state.input_data.design_seed is not None),
    }
    
    try:
        assert_tool_allowed("design", "geometry_generator")
    except ToolAuthorizationError as exc:
        return mark_tool_authorization_failure(
            state, "DesignAgent", "geometry_generator", exc
        )
    started_at = start_tool_timer()

    try:
        if previous_design is not None:
            preferences = preserve_revision_preferences(preferences, previous_design)
        plot_input = None
        seed = state.input_data.design_seed if state.input_data else None
        regeneration = state.input_data.regeneration if state.input_data else False
        excluded_plan_code = state.input_data.previous_base_plan_code if regeneration else None
        excluded_fingerprint = state.input_data.previous_design_fingerprint if regeneration else None

        from app.design.generation.spatial_planner import plan_spatial_program
        from app.design.geometry.geometry_generator import generate_geometry
        from app.design.generation.generation_service import prepare_inputs
        
        req, plot = prepare_inputs(land_size, terrain_type, preferences, plot_input, seed)
        program, _ = plan_spatial_program(req, plot, workflow_id=state.workflow_id)
        design, _ = generate_geometry(program, plot)
        
        gen_beds = sum(1 for r in design.rooms if 'bedroom' in r.room_type.lower())
        gen_baths = sum(1 for r in design.rooms if 'bathroom' in r.room_type.lower() or 'bath' in r.room_type.lower())
        additional = [r.room_type.title().replace("_", " ") for r in design.rooms if 'bedroom' not in r.room_type.lower() and 'bath' not in r.room_type.lower()]
        
        print("[Design Validation]")
        print("Requested:")
        print(f"Bedrooms={req.bedrooms} Bathrooms={req.bathrooms}\n")
        print("Generated:")
        print(f"Bedrooms={gen_beds} Bathrooms={gen_baths}\n")
        print("Additional spaces:")
        print(" ".join(additional))
        
        if gen_beds != req.bedrooms or gen_baths != req.bathrooms:
            raise GenerationFailure(f"Room mismatch. Expected {req.bedrooms} beds and {req.bathrooms} baths. Got {gen_beds} beds, {gen_baths} baths.", [{'failures': ['room_count_mismatch']}])
        
        quality = validate_architectural_quality(design, req=req, plot=plot)
        is_fallback = getattr(design, 'candidate_summary', {}).get('quality_status') == 'fallback'
        if not is_fallback and (not quality.passed or quality.status != 'VALID_HIGH_QUALITY'):
            raise GenerationFailure('Architectural quality validation failed.', [{'failures': quality.failures}])
        validation = validate_geometry(design.rooms, req.bedrooms, getattr(design, 'floor_count', req.floors), land_size,
                                       plot=plot, design=design)
        if not is_fallback and not validation.passed:
            raise GenerationFailure('Local geometry validation failed.', [{'failures': validation.failures}])
    except (GenerationFailure, ValueError) as exc:
        log_tool_failure(
            state=state,
            agent_name="design",
            tool_name="geometry_generator",
            started_at=started_at,
            input_summary=tool_input,
            error=exc,
        )
        state.design_result = None
        state.status = 'failed'
        state.approval_status = 'not_requested'
        state.validation_result = {
            'passed': False, 
            'failures': [str(exc)],
            'candidate_failures': getattr(exc, 'failures', []),
            'reason': 'No compatible catalogue plan exists'
        }
        state.execution_log.append(ExecutionLogEntry(
            agent_name='DesignAgent', action='Design generation failed; no layout submitted',
            tool_called='layout_generation_tool', result=str(exc),
            created_at_utc=datetime.now(timezone.utc).isoformat()))
        _persist_failure(state)
        with open("execution_log.json", "w") as f:
            import json
            f.write(json.dumps([e.model_dump() for e in state.execution_log], indent=2))
        return state
    log_tool_success(
        state=state,
        agent_name="design",
        tool_name="geometry_generator",
        started_at=started_at,
        input_summary=tool_input,
        output_summary={
            "room_count": len(design.rooms),
            "floor_count": design.floor_count,
            "total_built_up_area_sqft": design.total_built_up_area_sqft,
            "foundation_type": design.foundation_type,
            "quality_status": quality.status,
            "geometry_validation_passed": validation.passed,
        },
    )
    state.design_result = design.model_dump()
    state.ai_design_generated = True
    state.validation_result = validation.to_dict()
    
    # Submit to ASP.NET Core for persistence
    api_result = _submit_design(state)

    duration = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    plan_code = design.template_id or design.base_plan_code if hasattr(design, "base_plan_code") else design.template_id
    if revision_reason:
        action = f"Catalogue plan revised — reason: {revision_reason[:80]}"
    elif plan_code:
        action = f"Catalogue plan selected: {plan_code}"
    else:
        action = "Catalogue plan selected and room layout generated"

    state.execution_log.append(ExecutionLogEntry(
        agent_name="DesignAgent",
        action=action,
        tool_called="layout_generation_tool",
        duration_ms=duration,
        result=api_result,
        created_at_utc=datetime.now(timezone.utc).isoformat()
    ))

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
        )
        if response.ok:
            result_data = response.json()
            version = result_data.get('version')
            if isinstance(version, int):
                state.design_version = version
            print(f"[Design Agent] Design saved: version {result_data.get('version', '?')}, "
                  f"id {result_data.get('designId', '?')}")
            return "success"
        else:
            error_msg = f"api_failed: {response.status_code} - {response.text}"
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
            json={'status': 'failed', 'reason': _safe_failure_reason(state)},
            headers={'X-Internal-API-Key': INTERNAL_API_KEY},
            timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        state.execution_log.append(ExecutionLogEntry(
            agent_name='DesignAgent', action='Could not persist failed workflow status',
            result=type(exc).__name__, created_at_utc=datetime.now(timezone.utc).isoformat()))


def _safe_failure_reason(state: WorkflowState) -> str:
    """Return actionable validation text without stack traces or credentials."""
    validation = state.validation_result or {}
    details = validation.get('candidate_failures') or []
    messages = []
    for item in details[-3:]:
        messages.extend(item.get('failures', [])[:2])
    if not messages:
        messages = validation.get('failures', ['Design generation failed.'])
        
    if messages:
        first = str(messages[0]).strip()
        if first.startswith('{"code":'):
            import json
            try:
                data = json.loads(first)
                # If we exhausted the pool, there are no more alternatives.
                data['hasAlternatives'] = False 
                return json.dumps(data)
            except Exception:
                return first

    return ' '.join(str(message) for message in messages)[:1000]
