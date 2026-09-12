import pytest
from app.schemas.workflow_state import WorkflowState, CoordinatorInput
from app.agents.land_analysis_agent import land_analysis_node
from app.tools.vision_classify_tool import _parse_terrain_result, _safe_fallback

# Mocking the vision classify tool and ASP.NET API call is standard, 
# but we can test the fallback and routing logic directly.


def test_parse_terrain_rejects_invalid_terrain_value():
    raw = '{"terrain_type": "mountain", "slope_estimate": "moderate", "notable_features": []}'
    assert _parse_terrain_result(raw) is None


def test_safe_fallback_avoids_confident_classification():
    result = _safe_fallback('vision_parse_failed')
    assert result.terrain_type == 'unknown'
    assert result.slope_estimate == 'unknown'
    assert result.notable_features


def test_land_analysis_node_skip_if_manual():
    # If terrain is already populated by coordinator, it should skip vision
    state = WorkflowState(workflow_id="00000000-0000-0000-0000-000000000123")
    state.terrain_result = {"terrain_type": "hillside", "slope_estimate": "steep"}
    
    updated_state = land_analysis_node(state)
    
    # Should stay hillside
    assert updated_state.terrain_result["terrain_type"] == "hillside"
    assert updated_state.current_agent == "design"
    assert "Skipped vision" in updated_state.execution_log[-1].action

def test_land_analysis_node_fallback_no_photo():
    # If no photo is provided and no manual terrain, it must report unknown terrain
    state = WorkflowState(workflow_id="00000000-0000-0000-0000-000000000123")
    state.input_data = CoordinatorInput(
        submission_id="00000000-0000-0000-0000-000000000123", 
        budget_lkr=1.0, 
        land_size_perches=20.0,
        preferences={}
    )
    
    updated_state = land_analysis_node(state)
    
    assert updated_state.terrain_result["terrain_type"] == "unknown"
    assert updated_state.terrain_result["slope_estimate"] == "unknown"
    assert updated_state.current_agent == "design"
    assert "No photo URL" in updated_state.execution_log[-1].action
