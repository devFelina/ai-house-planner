from unittest.mock import Mock
from uuid import uuid4

import requests

from app.schemas.workflow_state import ExecutionLogEntry, WorkflowState
from app.utils import tool_audit_persistence as module


def _entry(action="tool_call_succeeded", **changes):
    values = {
        "agent_name": "design",
        "action": action,
        "tool_called": "geometry_generator",
        "duration_ms": 12,
        "result": "success",
        "event_status": "succeeded",
        "input_summary": {"bedrooms": 3},
        "output_summary": {"room_count": 8},
        "created_at_utc": "2026-10-02T00:00:00+00:00",
    }
    values.update(changes)
    return ExecutionLogEntry(**values)


def test_persist_calls_expected_endpoint_with_filtered_events(monkeypatch):
    workflow_id = uuid4()
    response = Mock(ok=True, status_code=200)
    request = Mock(return_value=response)
    monkeypatch.setattr(module.requests, "patch", request)
    log = [
        ExecutionLogEntry(
            agent_name="CoordinatorAgent", action="workflow_plan_created",
            result="ok", created_at_utc="2026-10-02T00:00:00+00:00"
        ),
        _entry(),
        _entry(
            action="tool_authorization_denied",
            agent_name="cost_estimation",
            tool_called="pricing_lookup",
            duration_ms=None,
            result="denied",
            event_status=None,
            input_summary=None,
            output_summary=None,
        ),
    ]

    assert module.persist_tool_audit_log(workflow_id, log) is True

    request.assert_called_once()
    call = request.call_args
    assert call.args[0].endswith(f"/internal/workflows/{workflow_id}/tool-audit-log")
    assert len(call.kwargs["json"]["entries"]) == 2
    assert {item["action"] for item in call.kwargs["json"]["entries"]} == {
        "tool_call_succeeded", "tool_authorization_denied"
    }
    assert call.kwargs["timeout"] == 10
    assert call.kwargs["headers"]["X-Internal-API-Key"] == module.INTERNAL_API_KEY


def test_transient_failure_retries_once_then_succeeds(monkeypatch):
    request = Mock(side_effect=[requests.ConnectionError("private endpoint"), Mock(ok=True)])
    sleep = Mock()
    monkeypatch.setattr(module.requests, "patch", request)
    monkeypatch.setattr(module.time, "sleep", sleep)

    assert module.persist_tool_audit_log(uuid4(), [_entry()]) is True
    assert request.call_count == 2
    sleep.assert_called_once_with(module.RETRY_DELAY_SECONDS)


def test_permanent_failure_is_non_fatal_and_does_not_mutate_state(monkeypatch):
    request = Mock(side_effect=requests.ConnectionError("secret connection details"))
    monkeypatch.setattr(module.requests, "patch", request)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    state = WorkflowState(workflow_id=uuid4(), status="running", execution_log=[_entry()])
    before = state.model_dump()

    assert module.persist_tool_audit_log(state.workflow_id, state.execution_log) is False
    assert request.call_count == 2
    assert state.model_dump() == before
    assert state.status == "running"


def test_payload_boundary_contains_no_unrelated_or_sensitive_values():
    payload = module.build_tool_audit_payload([
        _entry(
            input_summary={"region": "Colombo", "api_key": "[REDACTED]"},
            output_summary={"items_loaded": 4},
        )
    ])
    serialized = str(payload)

    assert "geometry_generator" in serialized
    assert "[REDACTED]" in serialized
    for forbidden in (
        "Bearer ", "X-Internal-API-Key", "raw prompt", "image_b64",
        "pricing_snapshot", "postgresql://"
    ):
        assert forbidden not in serialized


def test_success_logger_persists_complete_event(monkeypatch):
    from app.agents import design_agent
    from app.design.generation import generation_service, spatial_planner
    from app.design.geometry import geometry_generator
    from app.schemas.design_result import DesignResult, RoomLayout
    from app.orchestration import tool_audit
    from types import SimpleNamespace

    persisted = Mock(return_value=True)
    monkeypatch.setattr(tool_audit, "persist_tool_audit_log", persisted)
    requirements = SimpleNamespace(bedrooms=1, bathrooms=1, floors=1)
    design = DesignResult(
        floor_count=1, total_built_up_area_sqft=100,
        foundation_type="slab", terrain_type="flat",
        rooms=[
            RoomLayout(room_type="bedroom", floor=1, x=0, y=0, width=10, length=10),
            RoomLayout(room_type="bathroom", floor=1, x=10, y=0, width=5, length=5),
        ],
    )
    monkeypatch.setattr(generation_service, "prepare_inputs", lambda *_args, **_kwargs: (requirements, object()))
    monkeypatch.setattr(spatial_planner, "plan_spatial_program", lambda *_args, **_kwargs: (object(), {}))
    monkeypatch.setattr(geometry_generator, "generate_geometry", lambda *_args, **_kwargs: (design, {}))
    monkeypatch.setattr(
        design_agent, "validate_architectural_quality",
        lambda *_args, **_kwargs: SimpleNamespace(passed=True, status="VALID_HIGH_QUALITY", failures=[])
    )
    monkeypatch.setattr(
        design_agent, "validate_geometry",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True, failures=[], to_dict=lambda: {"passed": True, "failures": []}
        )
    )
    monkeypatch.setattr(design_agent, "_submit_design", lambda _state: "success")
    state = WorkflowState(
        workflow_id=uuid4(),
        input_data={
            "submission_id": str(uuid4()), "land_size_category": "medium",
            "land_size_perches": 10, "bedrooms": 1, "bathrooms": 1,
        },
    )

    design_agent.design_node(state)

    persisted.assert_called_once()
    sent_log = persisted.call_args.args[1]
    event = next(item for item in sent_log if item.action == "tool_call_succeeded")
    assert event.agent_name == "design"
    assert event.tool_called == "geometry_generator"
    assert event.duration_ms >= 0
    assert "rooms" not in event.output_summary


def test_pricing_failure_persists_before_rendering(monkeypatch):
    from app.orchestration import tool_audit
    from app.services import cost_estimation_service
    from app.tools.pricing_lookup_tool import PricingLookupError

    persisted = Mock(return_value=True)
    monkeypatch.setattr(tool_audit, "persist_tool_audit_log", persisted)
    monkeypatch.setattr(
        cost_estimation_service,
        "pricing_lookup_tool",
        Mock(side_effect=PricingLookupError("private response body")),
    )
    monkeypatch.setattr(cost_estimation_service, "_record_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cost_estimation_service, "_persist_failure", lambda *_args: None)
    state = WorkflowState(
        workflow_id=uuid4(),
        input_data={
            "submission_id": str(uuid4()), "land_size_category": "medium",
            "land_size_perches": 10,
        },
        design_result={
            "terrain_type": "flat", "total_built_up_area_sqft": 100,
            "rooms": [{"room_type": "bedroom", "area_sqft": 100}],
        },
    )

    cost_estimation_service.cost_estimation_node(state)

    assert state.status == "failed"
    persisted.assert_called_once()
    event = next(item for item in persisted.call_args.args[1] if item.action == "tool_call_failed")
    assert event.tool_called == "pricing_lookup"
    assert "private response body" not in event.model_dump_json()
