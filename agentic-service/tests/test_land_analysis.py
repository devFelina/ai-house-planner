import pytest
from app.schemas.workflow_agent import WorkflowState
from app.agents.land_analysis_agent import land_analysis_node
from app.schemas.workflow_agent import InputData

# Mocking the vision classify tool and ASP.NET API call is standard, 
# but we can test the fallback and routing logic directly.

def test_land_analysis_node_skip_if_manual():
    # If terrain is already populated by coordinator, it should skip vision
    state = WorkflowState(workflow_id="test-123")
    state.terrain_result = {"terrain_type": "hillside", "slope_estimate": "steep"}
    
    updated_state = land_analysis_node(state)
    
    # Should stay hillside
    assert updated_state.terrain_result["terrain_type"] == "hillside"
    assert updated_state.current_agent == "design"
    assert "Skipped vision" in updated_state.execution_log[-1].action

def test_land_analysis_node_fallback_no_photo():
    # If no photo is provided and no manual terrain, it should fallback to flat
    state = WorkflowState(workflow_id="test-123")
    state.input_data = InputData(submission_id="sub-1", budget_lkr=1.0, land_size_perches=10.0)
    
    updated_state = land_analysis_node(state)
    
    assert updated_state.terrain_result["terrain_type"] == "flat"
    assert updated_state.terrain_result["slope_estimate"] == "unknown"
    assert updated_state.current_agent == "design"
    assert "No photo URL" in updated_state.execution_log[-1].action
