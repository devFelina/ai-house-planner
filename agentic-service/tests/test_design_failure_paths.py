import json
from unittest.mock import MagicMock, patch
import pytest
from app.tools.layout_generation_tool import generate_layout
from app.design.candidate_generator import GenerationFailure
from app.schemas.workflow_state import CoordinatorInput, WorkflowState
from app.agents.design_agent import design_node
from app.workflows.house_planning_graph import app_graph


def state():
    return WorkflowState(workflow_id='00000000-0000-0000-0000-000000000123',
        input_data=CoordinatorInput(submission_id='00000000-0000-0000-0000-000000000123',
                                    land_size_perches=20, manual_terrain_type='flat',
                                    preferences={'bedrooms':3,'floors':1,'design_seed':1}),
        terrain_result={'terrain_type':'flat'})


def test_configured_api_failure_does_not_use_procedural_fallback():
    with patch('app.tools.layout_generation_tool.GOOGLE_API_KEY', 'test'), \
         patch('app.tools.layout_generation_tool._call_gemini_design', side_effect=RuntimeError('offline')):
        with pytest.raises(GenerationFailure, match='Gemini design generation failed'):
            generate_layout(20, 'flat', {'bedrooms':3,'floors':1})


def test_invalid_final_ai_retry_never_becomes_layout():
    with patch('app.tools.layout_generation_tool.GOOGLE_API_KEY', 'test'), \
         patch('app.tools.layout_generation_tool._call_gemini_design', return_value='{"rooms": [{"x": -999}]}') as call:
        with pytest.raises(GenerationFailure, match='Unable to produce valid AI geometry'):
            generate_layout(20, 'flat', {'bedrooms':3,'floors':1})
    assert call.call_count == 9


def test_ai_path_generates_three_valid_candidates_and_selects_highest_score():
    generated = [
        generate_layout(20, 'flat', {'bedrooms': 3, 'floors': 1}, design_seed=seed)
        for seed in (11, 22, 33)
    ]
    payloads = [json.dumps(item.model_dump()) for item in generated]
    fake_client = MagicMock()
    with patch('app.tools.layout_generation_tool.GOOGLE_API_KEY', 'test'), \
         patch('google.genai.Client', return_value=fake_client), \
         patch('app.tools.layout_generation_tool._call_gemini_design', side_effect=payloads) as call:
        result = generate_layout(20, 'flat', {'bedrooms': 3, 'floors': 1})

    assert call.call_count == 3
    assert result.candidate_summary['generation_mode'] == 'ai_generative'
    assert result.candidate_summary['generated_count'] == 3
    assert result.candidate_summary['valid_count'] == 3
    assert result.design_score == max(c['score'] for c in result.candidate_summary['candidates'])
    assert len(result.geometry_fingerprint) == 64


def test_seeded_request_never_calls_remote_advice():
    with patch('app.tools.layout_generation_tool._call_gemini_design') as call:
        a = generate_layout(20, 'flat', {'floors':1}, design_seed=8)
        b = generate_layout(20, 'flat', {'floors':1}, design_seed=8)
    call.assert_not_called()
    assert a.model_dump() == b.model_dump()


def test_failed_generation_is_not_submitted_or_approved():
    with patch('app.agents.design_agent.generate_layout', side_effect=GenerationFailure('no valid design')), \
         patch('app.agents.design_agent._submit_design') as submit, \
         patch('app.agents.design_agent._persist_failure'):
        result = app_graph.invoke(state())
    submit.assert_not_called()
    assert result['status'] == 'failed'
    assert result['design_result'] is None
    assert result['approval_status'] == 'not_requested'


def test_node_revalidates_before_persistence():
    invalid = generate_layout(20, 'flat', {'floors':1,'design_seed':1})
    invalid.rooms[0].x = 999
    with patch('app.agents.design_agent.generate_layout', return_value=invalid), \
         patch('app.agents.design_agent._submit_design') as submit, \
         patch('app.agents.design_agent._persist_failure'):
        result = design_node(state())
    submit.assert_not_called()
    assert result.status == 'failed'


def test_unknown_terrain_needs_manual_input():
    with pytest.raises(GenerationFailure, match='Terrain is unknown'):
        generate_layout(20, 'unknown', {'floors':1,'design_seed':1})
