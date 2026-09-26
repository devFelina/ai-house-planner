import json
from dataclasses import replace
from unittest.mock import MagicMock

import pytest
from fastapi import BackgroundTasks

from app.agents import design_agent
from app.design.catalogue import base_plan_library as library
from app.design.generation.candidate_generator import GenerationFailure
from app.design.generation.revision import preserve_revision_preferences
from app.design.program.room_counts import count_bathrooms
from app.main import ResumeWorkflowRequest, resume_workflow
from app.schemas.design_result import DesignResult
from app.design.generation import generation_service as generation


@pytest.fixture
def previous():
    plan = next(p for p in library.load_base_plan_catalog()
                if (p.bedrooms, p.bathrooms, p.floors) == (4, 2, 2))
    design = DesignResult.model_validate_json(plan.layout_json)
    design.candidate_summary = {'selected_plan_code': plan.plan_code, 'normalized_input': {
        'bedrooms': 4, 'bathrooms': 2, 'floors': 2, 'architectural_style': 'modern',
        'space_priority': 'balanced', 'open_plan': False,
    }}
    return design.model_dump()


@pytest.mark.parametrize('preferences,expected', [({}, 2), ({'bathrooms': None}, 2), ({'bathrooms': 3}, 3)])
def test_request_overrides_saved_bathrooms_only_when_supplied(previous, preferences, expected):
    result = preserve_revision_preferences(preferences, previous)
    assert result['bathrooms'] == expected
    assert result['bedrooms'] == 4
    assert result['style'] == 'modern'


def test_old_design_without_saved_requirements_uses_actual_rooms(previous):
    previous['candidate_summary'] = {}
    assert preserve_revision_preferences({'bedrooms': 4, 'floors': 2}, previous)['bathrooms'] == 2


def test_saved_requirement_takes_precedence_over_surplus_rooms(previous):
    previous['rooms'].append({**previous['rooms'][0], 'room_type': 'bathroom_attached'})
    assert count_bathrooms(previous['rooms']) == 3
    assert preserve_revision_preferences({}, previous)['bathrooms'] == 2


def test_explicit_preference_alias_overrides_saved_requirement(previous):
    previous['candidate_summary']['normalized_input']['master_ensuite'] = True
    result = preserve_revision_preferences({'master_ensuite': False}, previous)
    assert result['attached_bathroom'] is False
    assert result['bathrooms'] == 2


def resumed_state(previous):
    request = ResumeWorkflowRequest(
        workflow_id='00000000-0000-0000-0000-000000000123', resume_from='design',
        user_revision_prompt='make living room bigger', land_size_perches=20,
        preferences={'bedrooms': 4, 'floors': 2, 'style': 'modern'},
        previous_design=previous, terrain_result={'terrain_type': 'flat'},
        plot_constraints={'plot_width_ft': 70, 'plot_length_ft': 75})
    tasks = BackgroundTasks()
    resume_workflow(request, tasks, api_key='test')
    return tasks.tasks[0].args[0]


def test_resume_endpoint_passes_two_bathrooms_to_python_design_agent(previous, monkeypatch, tmp_path):
    state = resumed_state(previous)
    assert state.input_data.preferences['bathrooms'] == 2
    generate = MagicMock(side_effect=GenerationFailure('stop after capturing requirements'))
    monkeypatch.setattr(design_agent, 'generate_layout', generate)
    monkeypatch.chdir(tmp_path)
    design_agent.design_node(state)
    assert generate.call_args.kwargs['preferences']['bathrooms'] == 2


def test_design_agent_preserves_bathrooms_on_automatic_revision(previous, monkeypatch, tmp_path):
    state = resumed_state(previous)
    state.input_data.preferences.pop('bathrooms')
    state.user_revision_prompt = None
    generate = MagicMock(side_effect=GenerationFailure('stop after capturing requirements'))
    monkeypatch.setattr(design_agent, 'generate_layout', generate)
    monkeypatch.chdir(tmp_path)
    design_agent.design_node(state)
    assert generate.call_args.kwargs['preferences']['bathrooms'] == 2


@pytest.mark.parametrize('feedback', ['make living room bigger', 'Generate Another'])
def test_revision_candidate_filter_does_not_broaden_to_one_bath(previous, feedback, monkeypatch):
    records = [p for p in library.load_base_plan_catalog()
               if p.bedrooms == 4 and p.floors == 2 and p.bathrooms in (2, 3)]
    # A one-bath competitor exposes any accidental fallback to bathrooms=1.
    layout = json.loads(records[0].layout_json)
    baths = [room for room in layout['rooms'] if room['room_type'].startswith('bathroom')]
    baths[-1]['room_type'] = 'study'
    one_bath = replace(records[0], plan_code='ONE-BATH', bathrooms=1, layout_json=json.dumps(layout))
    monkeypatch.setattr(library, 'load_base_plan_catalog', lambda: [one_bath, *records])
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: None)
    result = generation.generate_layout(
        20, 'flat', {'bedrooms': 4, 'floors': 2}, previous_design=previous,
        revision_reason=feedback, plot_constraints={'plot_width_ft': 70, 'plot_length_ft': 75})
    assert result.candidate_summary['normalized_input']['bathrooms'] == 2
    assert 'ONE-BATH' not in result.candidate_summary['compatible_plan_codes']
    assert count_bathrooms(result.rooms) >= 2
