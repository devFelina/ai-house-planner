import pytest
from app.schemas.workflow_agent import WorkflowState, CoordinatorInput
from app.agents.design_agent import design_node
from app.tools.layout_generation_tool import select_template, generate_layout
from unittest.mock import patch


def test_select_template_for_hillside_three_bedroom_two_floor():
    template = select_template(bedrooms=3, floors=2, terrain_type='hillside', land_size_perches=10)
    assert template is not None
    assert template['template_id'] == '3BR_2F_HILLSIDE'
    assert template['name'] == 'HILLSIDE_STEPPED'
    assert 'layout' not in template
    assert template['min_width'] > 0


@patch('app.agents.design_agent._submit_design')
def test_design_node_generation(mock_submit):
    mock_submit.return_value = "success"
    
    state = WorkflowState(workflow_id="00000000-0000-0000-0000-000000000123")
    state.input_data = CoordinatorInput(
        submission_id="00000000-0000-0000-0000-000000000123", 
        budget_lkr=1.0, 
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

@patch('app.agents.design_agent._submit_design')
def test_design_node_revision_flow(mock_submit):
    mock_submit.return_value = "success"
    
    state = WorkflowState(workflow_id="00000000-0000-0000-0000-000000000123")
    state.input_data = CoordinatorInput(
        submission_id="00000000-0000-0000-0000-000000000123", 
        budget_lkr=1.0, 
        land_size_perches=10.0,
        preferences={"bedrooms": 3, "floors": 1}
    )
    state.terrain_result = {"terrain_type": "flat"}
    
    # Simulate a validation failure causing a revision
    state.validation_result = {"passed": False, "revision_reason": "Coverage limit exceeded"}
    state.design_result = {"dummy": "previous_design"}
    
    updated_state = design_node(state)
    
    assert updated_state.design_result is not None
    assert updated_state.current_agent == "cost_estimation"
    assert mock_submit.called
    assert "Revised design" in updated_state.execution_log[-1].action
