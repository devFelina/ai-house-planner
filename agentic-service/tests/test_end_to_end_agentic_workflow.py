from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.agents import design_agent, land_analysis_agent
from app.design.generation import generation_service, spatial_planner
from app.design.geometry import geometry_generator
from app.design.visualization import visualization_agent
from app.orchestration import tool_audit, workflow_router
from app.orchestration.tool_governance import assert_tool_allowed
from app.schemas.design_result import DesignResult, RoomLayout
from app.schemas.pricing_data import PricingItem
from app.schemas.workflow_plan import PlanStepStatus
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.services import construction_planning_service, cost_estimation_service, rendering_service
from app.tools.pricing_lookup_tool import PricingLookupError
from app.validation import design_validation_service
from app.workflows.house_planning_graph import app_graph


def _valid_design() -> DesignResult:
    room_types = ("living_room", "kitchen", "dining_area", "bedroom", "bathroom")
    return DesignResult(
        floor_count=1,
        total_built_up_area_sqft=500,
        foundation_type="slab",
        terrain_type="flat",
        rooms=[
            RoomLayout(
                room_type=room_type,
                floor=1,
                x=index * 10,
                y=0,
                width=10,
                length=10,
            )
            for index, room_type in enumerate(room_types)
        ],
    )


def _pricing_catalogue() -> list[PricingItem]:
    return [
        PricingItem(
            id=1,
            itemName="Standard materials",
            category="material",
            unitCostLkr=100,
            unit="per_sqft",
        ),
        PricingItem(
            id=2,
            itemName="Standard labour",
            category="labour",
            unitCostLkr=0.25,
            unit="factor",
        ),
    ]


def _initial_state() -> WorkflowState:
    return WorkflowState(
        workflow_id=uuid4(),
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            land_size_category="medium",
            land_size_perches=10,
            bedrooms=1,
            bathrooms=1,
            house_type="conventional",
        ),
    )


def _install_workflow_boundaries(monkeypatch, tmp_path, pricing_lookup):
    plan_snapshots: list[dict] = []
    audit_snapshots: list[list[dict]] = []

    def capture_plan(state: WorkflowState) -> None:
        plan_snapshots.append({
            "current_step_id": state.current_step_id,
            "completed_step_ids": list(state.completed_step_ids),
            "steps": [
                {"id": step.step_id, "agent": step.assigned_agent, "status": step.status.value}
                for step in state.plan.steps
            ],
        })

    def capture_audit(_workflow_id, execution_log) -> bool:
        audit_snapshots.append([
            entry.model_dump(mode="json", exclude_none=True)
            for entry in execution_log
            if entry.action.startswith("tool_")
        ])
        return True

    monkeypatch.setattr(workflow_router, "persist_workflow_plan_state", capture_plan)
    monkeypatch.setattr(tool_audit, "persist_tool_audit_log", capture_audit)
    monkeypatch.setattr(land_analysis_agent, "_persist_terrain", lambda _state: None)

    design = _valid_design()
    requirements = SimpleNamespace(bedrooms=1, bathrooms=1, floors=1)
    monkeypatch.setattr(
        generation_service,
        "prepare_inputs",
        lambda *_args, **_kwargs: (requirements, object()),
    )
    monkeypatch.setattr(
        spatial_planner,
        "plan_spatial_program",
        lambda *_args, **_kwargs: (object(), {}),
    )
    monkeypatch.setattr(
        geometry_generator,
        "generate_geometry",
        lambda *_args, **_kwargs: (design, {}),
    )
    monkeypatch.setattr(
        design_agent,
        "validate_architectural_quality",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True, status="VALID_HIGH_QUALITY", failures=[]
        ),
    )
    monkeypatch.setattr(
        design_agent,
        "validate_geometry",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=[],
            to_dict=lambda: {"passed": True, "failures": []},
        ),
    )
    monkeypatch.setattr(design_agent, "_submit_design", lambda _state: "success")

    monkeypatch.setattr(
        visualization_agent,
        "_existing_visualization",
        lambda _workflow_id: "https://assets.example.test/cached-plan.png",
    )

    construction_response = Mock(ok=True, status_code=200)
    monkeypatch.setattr(
        construction_planning_service.requests,
        "patch",
        Mock(return_value=construction_response),
    )
    monkeypatch.setattr(
        cost_estimation_service,
        "pricing_lookup_tool",
        pricing_lookup,
    )
    monkeypatch.setattr(cost_estimation_service, "_persist_cost_estimate", lambda *_args: None)
    monkeypatch.setattr(cost_estimation_service, "_record_run", lambda *_args, **_kwargs: None)
    validation_persistence_spy = Mock()
    monkeypatch.setattr(
        design_validation_service, "_submit_validation_result", validation_persistence_spy
    )

    monkeypatch.setattr(rendering_service, "OUTPUT_PLANS_DIR", tmp_path)
    timeline_spy = Mock()
    monkeypatch.setattr(rendering_service, "push_execution_log", timeline_spy)

    authorization_spies = {}
    for agent_name, module in {
        "design": design_agent,
        "construction_planning": construction_planning_service,
        "cost_estimation": cost_estimation_service,
    }.items():
        spy = Mock(wraps=assert_tool_allowed)
        monkeypatch.setattr(module, "assert_tool_allowed", spy)
        authorization_spies[agent_name] = spy

    return (
        plan_snapshots,
        audit_snapshots,
        authorization_spies,
        validation_persistence_spy,
        timeline_spy,
    )


def test_compiled_graph_reaches_human_approval_boundary(monkeypatch, tmp_path):
    (
        plan_snapshots,
        audit_snapshots,
        authorization_spies,
        validation_persistence_spy,
        timeline_spy,
    ) = _install_workflow_boundaries(
        monkeypatch, tmp_path, lambda **_kwargs: _pricing_catalogue()
    )
    initial_state = _initial_state()
    workflow_id = initial_state.workflow_id
    result = WorkflowState.model_validate(app_graph.invoke(initial_state))

    expected_step_ids = [f"S{number}" for number in range(1, 8)]
    expected_agents = [
        "requirement_analysis",
        "land_analysis",
        "design",
        "visualization",
        "construction_planning",
        "cost_estimation",
        "validation",
    ]
    assert result.status == "awaiting_approval"
    assert result.approval_status == "pending"
    assert result.approval_status not in {"approved", "rejected"}
    assert result.current_step_id is None
    assert result.completed_step_ids == expected_step_ids
    assert result.plan is not None
    assert len(result.plan.steps) == 7
    assert [step.step_id for step in result.plan.steps] == expected_step_ids
    assert [step.assigned_agent for step in result.plan.steps] == expected_agents
    assert all(step.status == PlanStepStatus.COMPLETED for step in result.plan.steps)

    running_transitions = {
        step["agent"]
        for snapshot in plan_snapshots
        for step in snapshot["steps"]
        if step["status"] == PlanStepStatus.RUNNING.value
        and snapshot["current_step_id"] == step["id"]
    }
    assert running_transitions == set(expected_agents)
    assert any(
        snapshot["current_step_id"] == "S1"
        and snapshot["completed_step_ids"] == []
        and snapshot["steps"][0]["status"] == PlanStepStatus.RUNNING.value
        for snapshot in plan_snapshots
    )
    assert any(
        snapshot["current_step_id"] is None
        and snapshot["completed_step_ids"] == expected_step_ids
        and all(step["status"] == PlanStepStatus.COMPLETED.value for step in snapshot["steps"])
        for snapshot in plan_snapshots
    )

    authorization_spies["design"].assert_called_once_with("design", "geometry_generator")
    authorization_spies["construction_planning"].assert_called_once_with(
        "construction_planning", "construction_scheduler"
    )
    authorization_spies["cost_estimation"].assert_called_once_with(
        "cost_estimation", "pricing_lookup"
    )

    audit_events = {
        event["tool_called"]: event
        for snapshot in audit_snapshots
        for event in snapshot
        if event.get("action") == "tool_call_succeeded"
    }
    for tool_name in ("geometry_generator", "construction_scheduler", "pricing_lookup"):
        event = audit_events[tool_name]
        assert event["event_status"] == "succeeded"
        assert event["duration_ms"] >= 0
        assert isinstance(event.get("input_summary"), dict)
        assert isinstance(event.get("output_summary"), dict)

    serialized_audits = str(audit_events).lower()
    for forbidden in (
        "api_key",
        "authorization",
        "x-internal-api-key",
        "response body",
        "raw_prompt",
        "pricing_snapshot",
        "room_id",
    ):
        assert forbidden not in serialized_audits

    assert result.terrain_result["terrain_type"] == "flat"
    assert result.design_result["floor_count"] == 1
    assert len(result.design_result["rooms"]) == 5
    assert result.construction_plan_result["phases"]
    assert result.cost_result["total_cost_lkr"] > 0
    assert result.validation_result["passed"] is True
    assert result.validation_result["is_valid"] is True
    assert result.validation_result["errors"] == []
    assert result.validation_result["summary"]
    assert len(result.validation_result["rules"]) == 4

    validation_persistence_spy.assert_called_once()
    timeline_spy.assert_called_once()
    assert any(
        entry.agent_name == "RenderingAgent" and entry.result == "success"
        for entry in result.execution_log
    )
    assert (tmp_path / f"plan_{workflow_id}.png").is_file()


def test_compiled_graph_stops_safely_when_pricing_lookup_fails(monkeypatch, tmp_path):
    pricing_tool = Mock(side_effect=PricingLookupError("test provider details must stay private"))
    (
        plan_snapshots,
        audit_snapshots,
        authorization_spies,
        validation_persistence_spy,
        timeline_spy,
    ) = _install_workflow_boundaries(monkeypatch, tmp_path, pricing_tool)
    initial_state = _initial_state()

    result = WorkflowState.model_validate(app_graph.invoke(initial_state))

    assert result.status == "failed"
    assert result.approval_status == "not_requested"
    assert result.approval_status not in {"pending", "approved"}
    assert result.current_step_id is None
    assert result.completed_step_ids == ["S1", "S2", "S3", "S4", "S5"]
    assert result.plan is not None
    assert [step.status for step in result.plan.steps] == [
        PlanStepStatus.COMPLETED,
        PlanStepStatus.COMPLETED,
        PlanStepStatus.COMPLETED,
        PlanStepStatus.COMPLETED,
        PlanStepStatus.COMPLETED,
        PlanStepStatus.FAILED,
        PlanStepStatus.PENDING,
    ]
    assert result.cost_result is None
    assert result.validation_result == {"passed": True, "failures": []}

    authorization_spies["cost_estimation"].assert_called_once_with(
        "cost_estimation", "pricing_lookup"
    )
    pricing_tool.assert_called_once()

    pricing_failures = [
        entry
        for entry in result.execution_log
        if entry.agent_name == "cost_estimation"
        and entry.tool_called == "pricing_lookup"
        and entry.action == "tool_call_failed"
    ]
    assert len(pricing_failures) == 1
    failure = pricing_failures[0]
    assert failure.event_status == "failed"
    assert failure.result == "failed"
    assert failure.duration_ms is not None and failure.duration_ms >= 0
    assert failure.error_type == "PricingLookupError"
    assert failure.error_summary == "Pricing service unavailable or returned invalid data."
    assert "test provider details" not in failure.model_dump_json()

    persisted_pricing_failures = [
        event
        for snapshot in audit_snapshots
        for event in snapshot
        if event.get("tool_called") == "pricing_lookup"
        and event.get("action") == "tool_call_failed"
    ]
    assert persisted_pricing_failures
    assert all(event["event_status"] == "failed" for event in persisted_pricing_failures)
    assert all("test provider details" not in str(event) for event in persisted_pricing_failures)

    prior_successes = {
        entry.tool_called
        for entry in result.execution_log
        if entry.action == "tool_call_succeeded" and entry.event_status == "succeeded"
    }
    assert {"geometry_generator", "construction_scheduler"}.issubset(prior_successes)
    assert "visualization_generator" not in prior_successes
    assert "requirement_extractor" not in prior_successes
    assert "terrain_classifier" not in prior_successes

    expected_statuses = [
        PlanStepStatus.COMPLETED.value,
        PlanStepStatus.COMPLETED.value,
        PlanStepStatus.COMPLETED.value,
        PlanStepStatus.COMPLETED.value,
        PlanStepStatus.COMPLETED.value,
        PlanStepStatus.FAILED.value,
        PlanStepStatus.PENDING.value,
    ]
    assert any(
        snapshot["current_step_id"] is None
        and snapshot["completed_step_ids"] == ["S1", "S2", "S3", "S4", "S5"]
        and [step["status"] for step in snapshot["steps"]] == expected_statuses
        for snapshot in plan_snapshots
    )

    validation_persistence_spy.assert_not_called()
    timeline_spy.assert_not_called()
    assert not any(entry.agent_name == "RenderingAgent" for entry in result.execution_log)
    assert list(tmp_path.glob("plan_*.png")) == []
