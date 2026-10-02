from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.orchestration.tool_governance import ToolAuthorizationError


def _state(**changes) -> WorkflowState:
    values = {
        "workflow_id": uuid4(),
        "input_data": CoordinatorInput(
            submission_id=uuid4(),
            land_size_category="medium",
            land_size_perches=10,
            bedrooms=1,
            bathrooms=1,
            natural_language_prompt="A compact one-bedroom house",
        ),
    }
    values.update(changes)
    return WorkflowState(**values)


def _deny(*_args, **_kwargs):
    raise ToolAuthorizationError("authorization denied for test")


def _assert_denied(state: WorkflowState, tool_name: str) -> None:
    assert state.status == "failed"
    entry = state.execution_log[-1]
    assert entry.action == "tool_authorization_denied"
    assert entry.tool_called == tool_name
    assert entry.result == "authorization denied for test"
    assert not any(
        item.action in {"tool_call_succeeded", "tool_call_failed"}
        for item in state.execution_log
    )


def test_requirement_denial_prevents_provider_call(monkeypatch):
    from app.agents import requirement_analysis_agent as module

    provider_call = Mock()
    monkeypatch.setattr(module, "assert_tool_allowed", _deny)
    monkeypatch.setattr(module._provider, "generate_json", provider_call)

    state = module.requirement_analysis_node(_state())

    provider_call.assert_not_called()
    _assert_denied(state, "requirement_extractor")


def test_land_denial_prevents_vision_and_fallback_retry(monkeypatch):
    from app.agents import land_analysis_agent as module

    vision_call = Mock()
    monkeypatch.setattr(module, "_photo_url_for_state", lambda _state: "https://example.test/land.jpg")
    monkeypatch.setattr(module, "assert_tool_allowed", _deny)
    monkeypatch.setattr(module, "vision_classification_tool", vision_call)

    state = module.land_analysis_node(_state())

    vision_call.assert_not_called()
    assert state.terrain_result is None
    _assert_denied(state, "terrain_classifier")


def test_land_without_photo_does_not_require_authorization(monkeypatch):
    from app.agents import land_analysis_agent as module

    authorization_check = Mock(side_effect=_deny)
    monkeypatch.setattr(module, "assert_tool_allowed", authorization_check)

    state = module.land_analysis_node(_state())

    authorization_check.assert_not_called()
    assert state.status == "running"
    assert state.terrain_result["terrain_type"] == "flat"


def test_design_denial_prevents_spatial_planning_and_geometry(monkeypatch):
    from app.agents import design_agent as module
    from app.design.generation import spatial_planner
    from app.design.geometry import geometry_generator

    planner_call = Mock()
    geometry_call = Mock()
    monkeypatch.setattr(module, "assert_tool_allowed", _deny)
    monkeypatch.setattr(spatial_planner, "plan_spatial_program", planner_call)
    monkeypatch.setattr(geometry_generator, "generate_geometry", geometry_call)

    state = module.design_node(_state())

    planner_call.assert_not_called()
    geometry_call.assert_not_called()
    assert state.design_result is None
    _assert_denied(state, "geometry_generator")


def _visualization_state() -> WorkflowState:
    return _state(design_result={
        "rooms": [
            {"room_type": "living_room"},
            {"room_type": "kitchen"},
            {"room_type": "dining_area"},
            {"room_type": "bedroom"},
            {"room_type": "bathroom"},
        ]
    })


def test_visualization_denial_on_cache_miss_prevents_provider_call(monkeypatch):
    from app.design.visualization import visualization_agent as module

    provider_call = Mock()
    monkeypatch.setattr(module, "_existing_visualization", lambda _workflow_id: None)
    monkeypatch.setattr(module, "ENABLE_AI_VISUALIZATION", True)
    monkeypatch.setattr(module, "assert_tool_allowed", _deny)
    monkeypatch.setattr(module.VisualizationAgent, "process", provider_call)

    state = module.visualization_node(_visualization_state())

    provider_call.assert_not_called()
    assert "ai_visualization" not in state.design_result
    _assert_denied(state, "visualization_generator")


def test_visualization_cache_hit_does_not_require_authorization(monkeypatch):
    from app.design.visualization import visualization_agent as module

    authorization_check = Mock(side_effect=_deny)
    monkeypatch.setattr(
        module, "_existing_visualization", lambda _workflow_id: "https://example.test/existing.png"
    )
    monkeypatch.setattr(module, "assert_tool_allowed", authorization_check)

    state = module.visualization_node(_visualization_state())

    authorization_check.assert_not_called()
    assert state.status == "running"
    assert state.design_result["ai_visualization"]["source"] == "persisted"


def test_construction_denial_prevents_scheduling(monkeypatch):
    from app.services import construction_planning_service as module

    phases_call = Mock()
    monkeypatch.setattr(module, "assert_tool_allowed", _deny)
    monkeypatch.setattr(module, "get_construction_phases", phases_call)

    state = module.construction_planning_node(_state(design_result={"rooms": []}))

    phases_call.assert_not_called()
    assert state.construction_plan_result is None
    _assert_denied(state, "construction_scheduler")


def test_cost_denial_prevents_pricing_lookup(monkeypatch):
    from app.services import cost_estimation_service as module

    pricing_call = Mock()
    monkeypatch.setattr(module, "assert_tool_allowed", _deny)
    monkeypatch.setattr(module, "pricing_lookup_tool", pricing_call)

    state = module.cost_estimation_node(_state(
        design_result={
            "terrain_type": "flat",
            "total_built_up_area_sqft": 100,
            "rooms": [{"room_type": "bedroom", "area_sqft": 100}],
        }
    ))

    pricing_call.assert_not_called()
    assert state.cost_result is None
    _assert_denied(state, "pricing_lookup")
