from types import SimpleNamespace
from unittest.mock import Mock, mock_open
from uuid import uuid4

import pytest

from app.design.exceptions import GenerationFailure
from app.providers.base_provider import ProviderUnavailableError
from app.schemas.design_result import DesignResult, RoomLayout
from app.schemas.pricing_data import PricingItem
from app.schemas.terrain_result import TerrainResult
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.tools.pricing_lookup_tool import PricingLookupError


def _state(**changes) -> WorkflowState:
    values = {
        "workflow_id": uuid4(),
        "input_data": CoordinatorInput(
            submission_id=uuid4(),
            land_size_category="medium",
            land_size_perches=10,
            bedrooms=1,
            bathrooms=1,
            natural_language_prompt="private prompt text that must not be logged",
            preferences={"home_office": True},
        ),
    }
    values.update(changes)
    return WorkflowState(**values)


def _events(state, tool_name):
    return [entry for entry in state.execution_log if entry.tool_called == tool_name and entry.action.startswith("tool_call_")]


def _design() -> DesignResult:
    room_types = ("living_room", "kitchen", "dining_area", "bedroom", "bathroom")
    return DesignResult(
        floor_count=1,
        total_built_up_area_sqft=500,
        foundation_type="slab",
        terrain_type="flat",
        rooms=[
            RoomLayout(
                room_type=room_type, floor=1, x=index * 10, y=0, width=10, length=10
            )
            for index, room_type in enumerate(room_types)
        ],
    )


def test_requirement_success_audits_only_approved_summaries(monkeypatch):
    from app.agents import requirement_analysis_agent as module

    monkeypatch.setattr(module, "execute_once", lambda _wid, _purpose, operation: (operation(), False))
    monkeypatch.setattr(module._provider, "generate_json", lambda **_kwargs: {
        "bedrooms": 1, "bathrooms": 1, "floors": None,
        "architecturalStyle": None, "homeOffice": True, "accessibility": None,
        "separateDining": None, "parkingRequired": None, "masterEnsuite": None,
    })

    state = module.requirement_analysis_node(_state())
    events = _events(state, "requirement_extractor")

    assert len(events) == 1
    event = events[0]
    assert event.action == "tool_call_succeeded"
    assert set(event.input_summary) == {"prompt_present", "prompt_chars", "explicit_preference_keys"}
    assert set(event.output_summary) == {
        "extracted_keys", "fields_extracted", "inferences_applied", "explicit_overrides"
    }
    assert event.input_summary["prompt_chars"] == len(state.input_data.natural_language_prompt)
    assert "private prompt text" not in event.model_dump_json()


def test_requirement_failure_is_audited_without_raw_error(monkeypatch):
    from app.agents import requirement_analysis_agent as module

    monkeypatch.setattr(module, "execute_once", lambda _wid, _purpose, operation: operation())
    monkeypatch.setattr(
        module._provider,
        "generate_json",
        Mock(side_effect=ProviderUnavailableError("provider-secret-response")),
    )

    state = module.requirement_analysis_node(_state())
    event = _events(state, "requirement_extractor")[0]

    assert event.action == "tool_call_failed"
    assert "provider-secret-response" not in event.model_dump_json()
    assert state.status == "running"


def test_land_vision_audit_excludes_url_contents(monkeypatch):
    from app.agents import land_analysis_agent as module

    raw_url = "https://private.example/land/photo.jpg?signature=do-not-log"
    monkeypatch.setattr(module, "_photo_url_for_state", lambda _state: raw_url)
    monkeypatch.setattr(
        module,
        "vision_classification_tool",
        lambda *_args, **_kwargs: TerrainResult(
            terrain_type="flat", slope_estimate="gentle", notable_features=["tree_cover"]
        ),
    )

    state = module.land_analysis_node(_state())
    event = _events(state, "terrain_classifier")[0]

    assert event.action == "tool_call_succeeded"
    assert set(event.input_summary) == {"has_image", "source_type", "scheme", "query_present"}
    assert set(event.output_summary) == {
        "terrain_type", "slope_estimate", "notable_feature_count", "fallback_used"
    }
    assert raw_url not in event.model_dump_json()
    assert "private.example" not in event.model_dump_json()


def test_land_no_photo_fallback_has_no_tool_event():
    from app.agents import land_analysis_agent as module

    state = module.land_analysis_node(_state())
    assert _events(state, "terrain_classifier") == []


def _install_design_success(monkeypatch):
    from app.agents import design_agent as module
    from app.design.generation import generation_service, spatial_planner
    from app.design.geometry import geometry_generator

    design = _design()
    requirements = SimpleNamespace(bedrooms=1, bathrooms=1, floors=1)
    monkeypatch.setattr(generation_service, "prepare_inputs", lambda *_args, **_kwargs: (requirements, object()))
    monkeypatch.setattr(spatial_planner, "plan_spatial_program", lambda *_args, **_kwargs: (object(), {}))
    monkeypatch.setattr(geometry_generator, "generate_geometry", lambda *_args, **_kwargs: (design, {}))
    monkeypatch.setattr(
        module, "validate_architectural_quality",
        lambda *_args, **_kwargs: SimpleNamespace(passed=True, status="VALID_HIGH_QUALITY", failures=[]),
    )
    monkeypatch.setattr(
        module, "validate_geometry",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True, failures=[], to_dict=lambda: {"passed": True, "failures": []}
        ),
    )
    monkeypatch.setattr(module, "_submit_design", lambda _state: "success")
    return module


def test_design_success_audits_summary_without_geometry(monkeypatch):
    module = _install_design_success(monkeypatch)
    state = module.design_node(_state())
    event = _events(state, "geometry_generator")[0]

    assert event.action == "tool_call_succeeded"
    assert set(event.input_summary) == {
        "bedrooms", "bathrooms", "floors", "land_size_perches", "terrain_type", "seed_present"
    }
    assert set(event.output_summary) == {
        "room_count", "floor_count", "total_built_up_area_sqft", "foundation_type",
        "quality_status", "geometry_validation_passed"
    }
    serialized = event.model_dump_json()
    assert '"rooms"' not in serialized
    assert '"x"' not in serialized


def test_design_failure_emits_one_sanitized_failure(monkeypatch):
    from app.agents import design_agent as module
    from app.design.generation import spatial_planner

    monkeypatch.setattr(
        spatial_planner,
        "plan_spatial_program",
        Mock(side_effect=GenerationFailure("private geometry details")),
    )
    monkeypatch.setattr(module, "_persist_failure", lambda _state: None)
    monkeypatch.setattr("builtins.open", mock_open())

    state = module.design_node(_state())
    events = _events(state, "geometry_generator")

    assert len(events) == 1
    assert events[0].action == "tool_call_failed"
    assert "private geometry details" not in events[0].model_dump_json()


def _visualization_state() -> WorkflowState:
    return _state(design_result=_design().model_dump())


def _visualization_common(monkeypatch, result):
    from app.design.visualization import visualization_agent as module

    monkeypatch.setattr(module, "_existing_visualization", lambda _wid: None)
    monkeypatch.setattr(module, "ENABLE_AI_VISUALIZATION", True)
    monkeypatch.setattr(module, "execute_once", lambda _wid, _purpose, operation: (operation(), False))
    monkeypatch.setattr(module.VisualizationAgent, "process", lambda *_args, **_kwargs: dict(result))
    monkeypatch.setattr(module, "_persist_visualization_status", lambda *_args: None)
    monkeypatch.setattr(module, "_persist_visualization", lambda *_args: None)
    monkeypatch.setattr(module, "_save_generated_image", lambda _result: "http://local/stable.png")
    return module


def test_visualization_success_emits_one_safe_event(monkeypatch):
    module = _visualization_common(monkeypatch, {
        "status": "validated", "model": "gpt-image-1", "image_b64": "raw-base64-secret"
    })
    state = module.visualization_node(_visualization_state())
    events = _events(state, "visualization_generator")

    assert len(events) == 1
    event = events[0]
    assert event.action == "tool_call_succeeded"
    assert set(event.input_summary) == {
        "room_count", "bedroom_count", "bathroom_count", "floor_count",
        "blueprint_input_present", "model", "image_size"
    }
    assert set(event.output_summary) == {
        "status", "model", "image_generated", "result_transport", "storage_reference_present"
    }
    assert "raw-base64-secret" not in event.model_dump_json()


def test_visualization_failed_status_emits_one_failure(monkeypatch):
    module = _visualization_common(monkeypatch, {
        "status": "failed", "model": "gpt-image-1", "error": "private-provider-body"
    })
    state = module.visualization_node(_visualization_state())
    events = _events(state, "visualization_generator")

    assert len(events) == 1
    assert events[0].action == "tool_call_failed"
    assert "private-provider-body" not in events[0].model_dump_json()


def test_visualization_cache_hit_emits_no_tool_event(monkeypatch):
    from app.design.visualization import visualization_agent as module

    monkeypatch.setattr(module, "_existing_visualization", lambda _wid: "https://stored/image.png")
    state = module.visualization_node(_visualization_state())
    assert _events(state, "visualization_generator") == []


def test_visualization_edit_generate_fallback_is_one_logical_event(monkeypatch):
    import httpx
    from app.design.visualization import openai_visualization_service as service_module

    fake_openai = Mock()
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.openai.test/images/edits"))
    fake_openai.images.edit.side_effect = service_module.BadRequestError(
        "Image edit is unsupported for this input", response=response, body={"code": "unsupported_operation"}
    )
    fake_openai.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(url=None, b64_json="generated-base64")]
    )
    monkeypatch.setattr(service_module, "openai", fake_openai)
    monkeypatch.setattr(service_module, "ENABLE_OPENAI", True)
    monkeypatch.setattr("app.services.ai_guard_db.check_daily_limit", lambda: None)
    monkeypatch.setattr("app.services.ai_guard_db.log_ai_cost", lambda *_args: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from app.design.visualization import visualization_agent as module
    monkeypatch.setattr(module, "_existing_visualization", lambda _wid: None)
    monkeypatch.setattr(module, "ENABLE_AI_VISUALIZATION", True)
    monkeypatch.setattr(module, "execute_once", lambda _wid, _purpose, operation: (operation(), False))
    monkeypatch.setattr(module, "_save_generated_image", lambda _result: "http://local/stable.png")
    monkeypatch.setattr(module, "_persist_visualization", lambda *_args: None)

    state = module.visualization_node(_visualization_state())

    assert fake_openai.images.edit.call_count == 1
    assert fake_openai.images.generate.call_count == 1
    assert len(_events(state, "visualization_generator")) == 1


def test_construction_success_audits_summary_without_schedule(monkeypatch):
    from app.services import construction_planning_service as module

    monkeypatch.setattr(module.requests, "patch", lambda *_args, **_kwargs: Mock(ok=True))
    state = module.construction_planning_node(_visualization_state())
    event = _events(state, "construction_scheduler")[0]

    assert event.action == "tool_call_succeeded"
    assert set(event.input_summary) == {
        "floor_count", "total_area_sqft", "terrain_type", "target_duration_days",
        "room_count", "bathroom_count"
    }
    assert set(event.output_summary) == {
        "phase_count", "total_duration_days", "schedule_status", "critical_path_length"
    }
    assert "phases" not in event.model_dump_json()


def _pricing() -> list[PricingItem]:
    return [
        PricingItem(id=1, itemName="Material", category="material", unitCostLkr=100, unit="per_sqft"),
        PricingItem(id=2, itemName="Labour", category="labour", unitCostLkr=0.25, unit="factor"),
    ]


def _cost_state() -> WorkflowState:
    return _state(design_result={
        "terrain_type": "flat",
        "total_built_up_area_sqft": 100,
        "rooms": [{"room_type": "bedroom", "area_sqft": 100}],
    })


def test_pricing_success_audits_counts_without_rows_or_prices(monkeypatch):
    from app.services import cost_estimation_service as module

    monkeypatch.setattr(module, "pricing_lookup_tool", lambda **_kwargs: _pricing())
    monkeypatch.setattr(module, "_persist_cost_estimate", lambda *_args: None)
    monkeypatch.setattr(module, "_record_run", lambda *_args, **_kwargs: None)
    state = module.cost_estimation_node(_cost_state())
    event = _events(state, "pricing_lookup")[0]

    assert event.action == "tool_call_succeeded"
    assert set(event.input_summary) == {"region", "quality_level"}
    assert set(event.output_summary) == {
        "items_loaded", "active_items", "material_item_count", "labour_item_count",
        "region", "quality_level"
    }
    serialized = event.model_dump_json()
    assert "unitCostLkr" not in serialized


def test_pricing_failure_audits_safely(monkeypatch):
    from app.services import cost_estimation_service as module

    monkeypatch.setattr(
        module,
        "pricing_lookup_tool",
        Mock(side_effect=PricingLookupError(
            "https://internal/pricing api-key-secret raw-response-body"
        )),
    )
    monkeypatch.setattr(module, "_record_run", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "_persist_failure", lambda *_args: None)
    state = module.cost_estimation_node(_cost_state())
    event = _events(state, "pricing_lookup")[0]

    assert event.action == "tool_call_failed"
    serialized = event.model_dump_json()
    assert "raw-response-body" not in serialized
    assert "api-key-secret" not in serialized
    assert "https://internal" not in serialized
