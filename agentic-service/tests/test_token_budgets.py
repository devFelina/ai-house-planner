"""Bounded AI selection calls and compact prompts, independent of API credentials."""
import json
from unittest.mock import MagicMock

import pytest

from app.design.exceptions import GenerationFailure
from app.design.generation import generation_service as generation

PREFERENCES = {'bedrooms': 4, 'bathrooms': 2, 'floors': 2, 'style': 'modern'}
PLOT = {'plot_width_ft': 70, 'plot_length_ft': 75}


@pytest.fixture
def provider(monkeypatch):
    mock = MagicMock(provider_name='offline', model_name='offline')
    # Deliberately invalid selection exercises fallback without another AI call.
    mock.generate_json.return_value = {
        'selected_plan_code': 'INVALID',
        'alternative_plan_codes': [],
        'design_intent': {
            'public_zone_orientation': 'south',
            'private_zone_orientation': 'north',
            'service_zone_orientation': 'west',
            'privacy_priority': 'balanced',
            'circulation_preference': 'short_central_hall',
        },
        'adaptations': {
            'mirror_horizontal': False,
            'mirror_vertical': False,
            'rotation_degrees': 0,
            'living_scale': 1.0,
            'bedroom_scale': 1.0,
            'entrance_side': 'south',
            'preserve_stair_core': True,
            'preserve_wet_core': True,
        },
        'reason_codes': ['plot_fit'],
    }
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: mock)
    return mock


def assert_compact_prompt(call):
    prompt = call.args[1]
    payload = json.loads(prompt)
    candidates = payload['candidate_plans']
    assert 1 <= len(candidates) <= 7
    assert len({p['geometry_fingerprint'] for p in candidates}) == len(candidates)
    required = {'plan_code', 'topology_family', 'geometry_fingerprint', 'suitability_score',
                'supported_features', 'plot_fit'}
    for candidate in candidates:
        assert required <= candidate.keys()
        assert len(candidate['geometry_fingerprint']) == 64
        assert not {'name', 'layout_json', 'LayoutJson', 'rooms', 'connections', 'entrances',
                    'x', 'y', 'width_array'} & candidate.keys()
        assert all(value is not None for value in candidate.values())
    # Bound user JSON separately from the provider's schema/envelope estimate.
    # Reserve request context plus compact metadata for each shortlisted candidate.
    assert len(prompt) <= 1400 + 800 * len(candidates)
    return payload


def test_ten_perch_failure_rejects_before_calling_ai(provider):
    with pytest.raises(GenerationFailure) as error:
        generation.generate_layout(
            10, 'flat', PREFERENCES, design_seed=42,
            plot_constraints={'plot_width_ft': 50, 'plot_length_ft': 50})
    # Since the 50x50 plot is too small for a (4, 2, 2) house, the candidate pool is empty.
    # The generation should fail before calling the AI.
    assert 'No compatible validated base plans exist' in str(error.value)
    provider.generate_json.assert_not_called()


def test_generate_another_calls_ai_once_per_request(provider):
    previous = generation.generate_layout(20, 'flat', PREFERENCES, design_seed=42, plot_constraints=PLOT)
    assert previous.candidate_summary['generation_mode'] == 'deterministic_fallback'
    provider.generate_json.assert_called_once()
    assert_compact_prompt(provider.generate_json.call_args)

    result = generation.generate_layout(
        20, 'flat', PREFERENCES, previous_design=previous.model_dump(),
        revision_reason='Generate Another', design_seed=43, plot_constraints=PLOT)
    assert result.candidate_summary['generation_mode'] == 'deterministic_fallback'
    assert result.geometry_fingerprint != previous.geometry_fingerprint
    assert provider.generate_json.call_count == 2
    payload = assert_compact_prompt(provider.generate_json.call_args)
    assert payload['generation_mode'] == 'generate_another'
    assert payload['previous_plan_code'] == previous.candidate_summary['selected_plan_code']
    assert payload['previous_fingerprint'] == previous.geometry_fingerprint


def test_simple_revision_calls_ai_again(provider):
    previous = generation.generate_layout(20, 'flat', PREFERENCES, design_seed=42, plot_constraints=PLOT)
    generation.generate_layout(
        20, 'flat', PREFERENCES, previous_design=previous.model_dump(),
        revision_reason='make living room bigger', design_seed=42, plot_constraints=PLOT)
    assert provider.generate_json.call_count == 2
    payload = assert_compact_prompt(provider.generate_json.call_args)
    assert payload['revision_reason'] == 'make living room bigger'
    assert payload['previous_fingerprint'] == previous.geometry_fingerprint
