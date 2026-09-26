from unittest.mock import MagicMock, patch

from app.agents.design_agent import design_node
from app.schemas.design_result import DesignResult
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.design.generation.generation_service import select_template


def test_select_template_for_hillside_three_bedroom_two_floor():
    template = select_template(bedrooms=3, floors=2, terrain_type='hillside', land_size_perches=10)
    assert template is not None
    assert template['plan_code'] == 'HILLSIDE_STEPPED'
    assert template['name'] == 'HILLSIDE_STEPPED'
    assert 'layout' not in template
    assert template['min_width'] > 0


@patch('app.agents.design_agent._submit_design')
def test_design_node_generation(mock_submit):
    mock_submit.return_value = "success"

    state = WorkflowState(workflow_id="00000000-0000-0000-0000-000000000123")
    state.input_data = CoordinatorInput(
        submission_id="00000000-0000-0000-0000-000000000123",
        land_size_perches=20.0,
        preferences={"bedrooms": 4, "floors": 2}
    )
    state.terrain_result = {"terrain_type": "flat"}

    updated_state = design_node(state)

    assert updated_state.design_result is not None
    assert updated_state.design_result["floor_count"] == 2
    # Template system now returns a real template ID (e.g. "4BR_2F_FLAT") on mock/quota-exceeded fallback.
    # "AI_GENERATED" is returned when the LLM succeeds. Either is valid.
    template_id = updated_state.design_result["template_id"]
    assert template_id is not None and len(template_id) > 0, "template_id must always be set"
    assert updated_state.current_agent == "cost_estimation"
    assert mock_submit.called

@patch('app.agents.design_agent.validate_geometry')
@patch('app.agents.design_agent.validate_architectural_quality')
@patch('app.agents.design_agent.generate_layout')
@patch('app.agents.design_agent._submit_design')
def test_design_node_revision_flow(mock_submit, mock_generate, mock_quality, mock_geometry):
    mock_submit.return_value = "success"
    mock_quality.return_value = MagicMock(passed=True, status='VALID_HIGH_QUALITY')
    mock_geometry.return_value = MagicMock(passed=True)

    state = WorkflowState(workflow_id="00000000-0000-0000-0000-000000000123")
    state.input_data = CoordinatorInput(
        submission_id="00000000-0000-0000-0000-000000000123",
        land_size_perches=10.0,
        preferences={"bedrooms": 3, "bathrooms": 2, "floors": 1}
    )
    state.terrain_result = {"terrain_type": "flat"}

    # Simulate a validation failure causing a revision
    state.validation_result = {"passed": False, "revision_reason": "Coverage limit exceeded"}
    valid_design = DesignResult(
        design_id="test", floor_count=1, total_built_up_area_sqft=1000, ground_footprint_sqft=1000,
        foundation_type="slab", terrain_type="flat", template_family="COMPACT_RECTANGLE", template_id="HP-3B1B-1F-1",
        rooms=[], connections=[], entrances=[], plot_constraints={}
    )
    state.design_result = valid_design.model_dump()
    mock_generate.return_value = valid_design

    updated_state = design_node(state)

    assert updated_state.design_result is not None
    assert updated_state.current_agent == "cost_estimation"
    assert mock_submit.called
    assert "Revised design" in updated_state.execution_log[-1].action
    assert mock_generate.call_args.kwargs['preferences']['bathrooms'] == 2
