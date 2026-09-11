import pytest
from app.schemas.workflow_agent import WorkflowState, InputData
from app.agents.design_agent import design_node
from unittest.mock import patch

@patch('app.agents.design_agent._submit_design')
def test_design_node_generation(mock_submit):
    mock_submit.return_value = "success"
    
    state = WorkflowState(workflow_id="test-123")
    state.input_data = InputData(
        submission_id="sub-1", 
        budget_lkr=1.0, 
        land_size_perches=20.0,
        preferences={"bedrooms": 4, "floors": 2}
    )
    state.terrain_result = {"terrain_type": "flat"}
    
    updated_state = design_node(state)
    
    assert updated_state.design_result is not None
    assert updated_state.design_result["floor_count"] == 2
    assert updated_state.design_result["template_id"] == "4BR_2F_FLAT"
    assert updated_state.current_agent == "cost_estimation"
    assert mock_submit.called

@patch('app.agents.design_agent._submit_design')
def test_design_node_revision_flow(mock_submit):
    mock_submit.return_value = "success"
    
    state = WorkflowState(workflow_id="test-123")
    state.input_data = InputData(
        submission_id="sub-1", 
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
