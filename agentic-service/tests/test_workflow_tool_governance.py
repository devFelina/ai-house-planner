from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from langgraph.graph import END

from app.agents import design_agent, land_analysis_agent, requirement_analysis_agent
from app.design.generation import generation_service, spatial_planner
from app.design.geometry import geometry_generator
from app.design.visualization import visualization_agent
from app.orchestration.tool_governance import (
    AGENT_TOOL_ALLOWLIST,
    KNOWN_TOOLS,
    ToolAuthorizationError,
    assert_tool_allowed,
)
from app.orchestration.workflow_router import coordinator_node
from app.schemas.design_result import DesignResult, RoomLayout
from app.schemas.pricing_data import PricingItem
from app.schemas.terrain_result import TerrainResult
from app.schemas.validation_schemas import ValidationResult
from app.schemas.workflow_plan import PlanStepStatus
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.services import construction_planning_service, cost_estimation_service
from app.validation import design_validation_service
from app.workflows.house_planning_graph import route_from_coordinator


GOVERNED_PAIRS = {
    "requirement_analysis": "requirement_extractor",
    "land_analysis": "terrain_classifier",
    "design": "geometry_generator",
    "visualization": "visualization_generator",
    "construction_planning": "construction_scheduler",
    "cost_estimation": "pricing_lookup",
}


def _state() -> WorkflowState:
    return WorkflowState(
        workflow_id=uuid4(),
        input_data=CoordinatorInput(
            submission_id=uuid4(),
            land_size_category="medium",
            land_size_perches=10,
            bedrooms=1,
            bathrooms=1,
            natural_language_prompt="A compact one-bedroom home",
        ),
    )


def _design() -> DesignResult:
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


def _pricing() -> list[PricingItem]:
    return [
        PricingItem(
            id=1,
            itemName="Materials",
            category="material",
            unitCostLkr=100,
            unit="per_sqft",
        ),
        PricingItem(
            id=2,
            itemName="Labour",
            category="labour",
            unitCostLkr=0.25,
            unit="factor",
        ),
    ]


def _install_success_stubs(monkeypatch):
    generated_design = _design()

    monkeypatch.setattr(
        requirement_analysis_agent,
        "execute_once",
        lambda _workflow_id, _purpose, operation: (operation(), False),
    )
    monkeypatch.setattr(
        requirement_analysis_agent._provider,
        "generate_json",
        lambda **_kwargs: {
            "bedrooms": 1,
            "bathrooms": 1,
            "floors": 1,
            "architecturalStyle": None,
            "homeOffice": None,
            "accessibility": None,
            "separateDining": None,
            "parkingRequired": None,
            "masterEnsuite": None,
        },
    )

    monkeypatch.setattr(land_analysis_agent, "_photo_url_for_state", lambda _state: "https://example.test/land.jpg")
    monkeypatch.setattr(
        land_analysis_agent,
        "vision_classification_tool",
        lambda *_args, **_kwargs: TerrainResult(
            terrain_type="flat", slope_estimate="flat", notable_features=[]
        ),
    )

    requirements = SimpleNamespace(bedrooms=1, bathrooms=1, floors=1)
    monkeypatch.setattr(generation_service, "prepare_inputs", lambda *_args, **_kwargs: (requirements, object()))
    monkeypatch.setattr(spatial_planner, "plan_spatial_program", lambda *_args, **_kwargs: (object(), {}))
    monkeypatch.setattr(geometry_generator, "generate_geometry", lambda *_args, **_kwargs: (generated_design, {}))
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
            passed=True, failures=[], to_dict=lambda: {"passed": True, "failures": []}
        ),
    )
    monkeypatch.setattr(design_agent, "_submit_design", lambda _state: "success")

    monkeypatch.setattr(visualization_agent, "_existing_visualization", lambda _workflow_id: None)
    monkeypatch.setattr(visualization_agent, "ENABLE_AI_VISUALIZATION", True)
    monkeypatch.setattr(
        visualization_agent,
        "execute_once",
        lambda _workflow_id, _purpose, operation: (operation(), False),
    )
    monkeypatch.setattr(
        visualization_agent.VisualizationAgent,
        "process",
        lambda *_args, **_kwargs: {"image_url": None, "status": "failed"},
    )
    monkeypatch.setattr(visualization_agent, "_persist_visualization_status", lambda *_args: None)

    response = Mock(ok=True, status_code=200)
    monkeypatch.setattr(construction_planning_service.requests, "patch", lambda *_args, **_kwargs: response)

    monkeypatch.setattr(cost_estimation_service, "pricing_lookup_tool", lambda **_kwargs: _pricing())
    monkeypatch.setattr(cost_estimation_service, "_persist_cost_estimate", lambda *_args: None)
    monkeypatch.setattr(cost_estimation_service, "_record_run", lambda *_args, **_kwargs: None)

    monkeypatch.setattr(
        design_validation_service,
        "validate_house_plan",
        lambda _state: ValidationResult(passed=True, summary="passed"),
    )
    monkeypatch.setattr(design_validation_service, "_submit_validation_result", lambda *_args: None)


def _authorization_spies(monkeypatch) -> dict[str, Mock]:
    modules = {
        "requirement_analysis": requirement_analysis_agent,
        "land_analysis": land_analysis_agent,
        "design": design_agent,
        "visualization": visualization_agent,
        "construction_planning": construction_planning_service,
        "cost_estimation": cost_estimation_service,
    }
    spies = {}
    for agent_name, module in modules.items():
        spy = Mock(wraps=assert_tool_allowed)
        monkeypatch.setattr(module, "assert_tool_allowed", spy)
        spies[agent_name] = spy
    return spies


def _run_selected_agent(state: WorkflowState, nodes: dict[str, object]) -> WorkflowState:
    selected = route_from_coordinator(state)
    assert selected == state.plan.steps[int(state.current_step_id[1:]) - 1].assigned_agent
    return nodes[selected](state)


def test_plan_driven_workflow_enforces_all_six_governed_pairs(monkeypatch):
    _install_success_stubs(monkeypatch)
    spies = _authorization_spies(monkeypatch)
    nodes = {
        "requirement_analysis": requirement_analysis_agent.requirement_analysis_node,
        "land_analysis": land_analysis_agent.land_analysis_node,
        "design": design_agent.design_node,
        "visualization": visualization_agent.visualization_node,
        "construction_planning": construction_planning_service.construction_planning_node,
        "cost_estimation": cost_estimation_service.cost_estimation_node,
        "validation": design_validation_service.validation_node,
    }

    state = _state()
    for expected_agent in (*GOVERNED_PAIRS, "validation"):
        state = coordinator_node(state)
        assert route_from_coordinator(state) == expected_agent
        state = _run_selected_agent(state, nodes)

    state = coordinator_node(state)

    assert all(step.status == PlanStepStatus.COMPLETED for step in state.plan.steps)
    assert route_from_coordinator(state) == "rendering"
    for agent_name, tool_name in GOVERNED_PAIRS.items():
        spies[agent_name].assert_called_once_with(agent_name, tool_name)
    assert not hasattr(design_validation_service, "assert_tool_allowed")


def test_workflow_stops_when_design_geometry_is_unauthorized(monkeypatch):
    _install_success_stubs(monkeypatch)
    planner_call = Mock()
    geometry_call = Mock()
    monkeypatch.setattr(spatial_planner, "plan_spatial_program", planner_call)
    monkeypatch.setattr(geometry_generator, "generate_geometry", geometry_call)

    def deny_design(agent_name, tool_name):
        raise ToolAuthorizationError(
            f"Agent '{agent_name}' is not allowed to use tool '{tool_name}'"
        )

    monkeypatch.setattr(design_agent, "assert_tool_allowed", deny_design)
    nodes = {
        "requirement_analysis": requirement_analysis_agent.requirement_analysis_node,
        "land_analysis": land_analysis_agent.land_analysis_node,
        "design": design_agent.design_node,
    }

    state = _state()
    for expected_agent in ("requirement_analysis", "land_analysis", "design"):
        state = coordinator_node(state)
        assert route_from_coordinator(state) == expected_agent
        state = _run_selected_agent(state, nodes)

    planner_call.assert_not_called()
    geometry_call.assert_not_called()
    assert state.status == "failed"

    state = coordinator_node(state)
    assert state.plan.steps[0].status == PlanStepStatus.COMPLETED
    assert state.plan.steps[1].status == PlanStepStatus.COMPLETED
    assert state.plan.steps[2].status == PlanStepStatus.FAILED
    assert all(step.status == PlanStepStatus.PENDING for step in state.plan.steps[3:])
    assert route_from_coordinator(state) == END

    denial = next(entry for entry in state.execution_log if entry.action == "tool_authorization_denied")
    assert denial.agent_name == "DesignAgent"
    assert denial.tool_called == "geometry_generator"
    serialized = denial.model_dump_json()
    for forbidden in (
        "A compact one-bedroom home",
        "api_key",
        "Authorization",
        "Traceback",
        "image_bytes",
    ):
        assert forbidden not in serialized


def test_real_agent_governance_references_match_policy():
    assert set(GOVERNED_PAIRS).issubset(AGENT_TOOL_ALLOWLIST)
    assert set(GOVERNED_PAIRS.values()).issubset(KNOWN_TOOLS)
    for agent_name, tool_name in GOVERNED_PAIRS.items():
        assert tool_name in AGENT_TOOL_ALLOWLIST[agent_name]
