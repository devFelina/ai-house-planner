"""Provider call, failover, and persisted selection metadata tests."""
import json
from unittest.mock import MagicMock

from app.design.generation import generation_service as generation

PREFERENCES = {'bedrooms': 3, 'bathrooms': 2, 'floors': 1, 'style': 'Modern Minimalist'}
PLOT = {'plot_width_ft': 90, 'plot_length_ft': 65, 'road_side': 'south'}


def decision_for_prompt(_system, user_prompt, _schema):
    candidate = json.loads(user_prompt)['candidate_plans'][0]
    return {
        'selected_plan_code': candidate['plan_code'],
        'alternative_plan_codes': [],
        'design_intent': {
            'public_zone_orientation': 'south', 'private_zone_orientation': 'north',
            'service_zone_orientation': 'west', 'privacy_priority': 'balanced',
            'circulation_preference': 'short_central_hall',
        },
        'adaptations': {
            'mirror_horizontal': False, 'mirror_vertical': False, 'rotation_degrees': 0,
            'living_scale': 1.0, 'bedroom_scale': 1.0, 'entrance_side': 'south',
            'preserve_stair_core': True, 'preserve_wet_core': True,
        },
        'reason_codes': ['plot_fit', 'style_match'],
    }


def provider(name='openai', model='gpt-test', effect=decision_for_prompt):
    mock = MagicMock(provider_name=name, model_name=model)
    mock.generate_json.side_effect = effect
    return mock


def generate(**kwargs):
    return generation.generate_layout(20, 'flat', PREFERENCES,
                                      plot_constraints=PLOT, design_seed=11, **kwargs)


def previous_without_ai(monkeypatch):
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: None)
    return generate()


def test_normal_generation_calls_ai_once_and_persists_provider_metadata(monkeypatch, caplog):
    openai = provider()
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: openai)
    caplog.set_level('INFO', logger='app.design.generation.generation_service')
    result = generate()
    assert openai.generate_json.call_count == 1
    assert result.candidate_summary['generation_mode'] == 'ai_adapted_template'
    assert result.candidate_summary['provider'] == 'openai'
    assert result.candidate_summary['model'] == 'gpt-test'
    assert result.candidate_summary['ai_ran'] is True
    assert result.candidate_summary['selected_plan_code']
    assert result.geometry_fingerprint
    entry = next(record.getMessage() for record in caplog.records if '[AI Agent]' in record.getMessage())
    for field in ('request_type=generation', 'provider=openai', 'model=gpt-test',
                  'candidate_count=', 'selected_plan=', 'reason_codes=',
                  'generation_mode=ai_adapted_template'):
        assert field in entry
    assert 'layout_json' not in entry and 'api_key' not in entry


def test_generate_another_calls_ai_once_with_previous_context(monkeypatch):
    previous = previous_without_ai(monkeypatch)
    openai = provider()
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: openai)
    result = generate(previous_design=previous.model_dump(), revision_reason='Generate Another')
    assert openai.generate_json.call_count == 1
    prompt = json.loads(openai.generate_json.call_args.args[1])
    assert prompt['previous_plan_code'] == previous.candidate_summary['selected_plan_code']
    assert prompt['previous_fingerprint'] == previous.geometry_fingerprint
    assert all(candidate['geometry_fingerprint'] for candidate in prompt['candidate_plans'])
    assert result.geometry_fingerprint != previous.geometry_fingerprint
    assert result.candidate_summary['generation_mode'] == 'ai_adapted_template'


def test_revision_calls_ai_once_with_request_and_current_context(monkeypatch):
    previous = previous_without_ai(monkeypatch)
    openai = provider()
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: openai)
    result = generate(previous_design=previous.model_dump(), revision_reason='make living room bigger')
    assert openai.generate_json.call_count == 1
    prompt = json.loads(openai.generate_json.call_args.args[1])
    assert prompt['revision_reason'] == 'make living room bigger'
    assert prompt['normalized_input']['bathrooms'] == 2
    assert prompt['previous_plan_code'] == previous.candidate_summary['selected_plan_code']
    assert prompt['previous_fingerprint'] == previous.geometry_fingerprint
    assert prompt['candidate_plans']
    assert result.candidate_summary['reason_codes'] == ['plot_fit', 'style_match']


def test_openai_failure_calls_ollama_and_uses_ollama_result(monkeypatch):
    openai = provider(effect=RuntimeError('openai unavailable'))
    ollama = provider('ollama', 'qwen-test')
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: openai)
    monkeypatch.setattr(generation, 'get_next_design_provider',
                        lambda name: ollama if name == 'openai' else None)
    result = generate()
    assert openai.generate_json.call_count == 1
    assert ollama.generate_json.call_count == 1
    assert result.candidate_summary['provider'] == 'ollama'
    assert result.candidate_summary['model'] == 'qwen-test'
    assert result.candidate_summary['generation_mode'] == 'ai_adapted_template'


def test_all_provider_failures_use_honest_deterministic_fallback(monkeypatch):
    openai = provider(effect=RuntimeError('openai unavailable'))
    ollama = provider('ollama', 'qwen-test', RuntimeError('ollama unavailable'))
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: openai)
    monkeypatch.setattr(generation, 'get_next_design_provider',
                        lambda name: ollama if name == 'openai' else None)
    result = generate()
    assert openai.generate_json.call_count == 1
    assert ollama.generate_json.call_count == 1
    assert result.candidate_summary['generation_mode'] == 'deterministic_fallback'
    assert result.candidate_summary['provider'] is None
    assert result.candidate_summary['model'] is None
    assert result.candidate_summary['ai_ran'] is True
    assert result.candidate_summary['attempted_providers'] == ['openai', 'ollama']
