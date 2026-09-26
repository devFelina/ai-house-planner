"""Catalogue novelty checks using existing seed geometry and offline providers."""
import json
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from app.design.catalogue.base_plan_library import load_base_plan_catalog
from app.design.generation.candidate_generator import GenerationFailure
from app.design.generation.diversity import geometry_fingerprint
from app.design.generation.plan_adapter import PlanAdapter, transform_design
from app.schemas.design_result import DesignResult
from app.design.generation import generation_service as generation

PREFERENCES = {'bedrooms': 2, 'bathrooms': 1, 'floors': 1}
PLOT = {'plot_width_ft': 90, 'plot_length_ft': 90}


@pytest.fixture
def plans(monkeypatch):
    source = next(p for p in load_base_plan_catalog()
                  if (p.bedrooms, p.bathrooms, p.floors) == (2, 1, 1))
    req, plot = generation.prepare_inputs(30, 'flat', PREFERENCES, PLOT)
    decision = generation._fallback_decision([source], req, plot)
    design = PlanAdapter().adapt(source, decision, req, plot)
    first = replace(source, plan_code='A', layout_json=design.model_dump_json())
    duplicate = replace(first, plan_code='A-COPY', name='Another name')
    mirrored = transform_design(design, mirror_horizontal=True)
    distinct = replace(first, plan_code='B', layout_json=mirrored.model_dump_json())
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: None)
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: [first, duplicate, distinct])
    return first, duplicate, distinct


def generate(previous=None, reason='Generate Another'):
    return generation.generate_layout(30, 'flat', PREFERENCES, previous_design=previous,
                                      revision_reason=reason if previous else None,
                                      plot_constraints=PLOT)


def previous_design(plan):
    design = DesignResult.model_validate_json(plan.layout_json)
    design.candidate_summary = {'selected_plan_code': plan.plan_code}
    # Simulate a stored fingerprint from before the canonicalization upgrade.
    design.geometry_fingerprint = '0' * 64
    return design.model_dump()


def provider_for(monkeypatch, plans, selected='A', alternatives=()):
    req, plot = generation.prepare_inputs(30, 'flat', PREFERENCES, PLOT)
    decision = generation._fallback_decision(plans, req, plot).model_copy(update={
        'selected_plan_code': selected, 'alternative_plan_codes': list(alternatives)})
    provider = MagicMock(provider_name='test', model_name='offline')
    provider.generate_json.return_value = decision.model_dump()
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: provider)
    return provider


def test_identical_codes_share_one_ai_shortlist_entry(plans, monkeypatch):
    provider = provider_for(monkeypatch, plans)
    generate()
    prompt = json.loads(provider.generate_json.call_args.args[1])
    candidates = prompt['candidate_plans']
    assert [p['plan_code'] for p in candidates] == ['A', 'B']
    assert len({p['geometry_fingerprint'] for p in candidates}) == 2
    assert all(p['topology_family'] for p in candidates)
    assert all('layout_json' not in p and 'rooms' not in p for p in candidates)
    provider.generate_json.assert_called_once()


def test_generate_another_excludes_previous_geometry_before_ai(plans, monkeypatch):
    provider = provider_for(monkeypatch, plans, selected='B')
    result = generate(previous_design(plans[0]))
    assert result.geometry_fingerprint != plans[0].geometry_fingerprint
    prompt = json.loads(provider.generate_json.call_args.args[1])
    assert [p['plan_code'] for p in prompt['candidate_plans']] == ['B']
    assert prompt['previous_fingerprint'] == plans[0].geometry_fingerprint
    assert prompt['previous_plan_code'] == 'A'
    assert prompt['generation_mode'] == 'generate_another'


def test_only_duplicates_fail_before_ai(plans, monkeypatch):
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: list(plans[:2]))
    provider = provider_for(monkeypatch, plans)
    with pytest.raises(GenerationFailure, match=generation.NO_DISTINCT_LAYOUT):
        generate(previous_design(plans[0]))
    provider.generate_json.assert_not_called()


@pytest.mark.parametrize('provider_fails', [False, True])
def test_fallback_uses_distinct_geometry(plans, monkeypatch, provider_fails):
    if provider_fails:
        provider = provider_for(monkeypatch, plans)
        provider.generate_json.side_effect = RuntimeError('offline')
    result = generate(previous_design(plans[0]))
    assert result.candidate_summary['selected_plan_code'] == 'B'
    assert result.candidate_summary['generation_mode'] == (
        'deterministic_fallback' if provider_fails else 'deterministic_template_selection')
    assert result.geometry_fingerprint != plans[0].geometry_fingerprint


def test_fallback_helper_filters_fingerprints_not_codes(plans):
    req, plot = generation.prepare_inputs(30, 'flat', PREFERENCES, PLOT)
    decision = generation._fallback_decision(plans, req, plot, 'A', plans[0].geometry_fingerprint)
    assert decision.selected_plan_code == 'B'
    assert decision.alternative_plan_codes == []
    with pytest.raises(GenerationFailure, match=generation.NO_DISTINCT_LAYOUT):
        generation._fallback_decision(plans[:2], req, plot, 'A', plans[0].geometry_fingerprint)


def test_post_adapter_duplicate_tries_next_ai_alternative(plans, monkeypatch):
    # The seed entrance differs, but adaptation restores the previous geometry.
    raw = DesignResult.model_validate_json(plans[0].layout_json)
    raw.entrances[0].offset += 0.25
    converges = replace(plans[0], plan_code='A-RAW', layout_json=raw.model_dump_json())
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: [converges, plans[2]])
    provider_for(monkeypatch, [converges, plans[2]], selected='A-RAW', alternatives=['B'])
    result = generate(previous_design(plans[0]))
    assert result.candidate_summary['selected_plan_code'] == 'B'
    assert result.candidate_summary['tried_plan_codes'] == ['A-RAW', 'B']
    assert result.candidate_summary['generation_mode'] == 'ai_adapted_template'
    assert result.geometry_fingerprint != plans[0].geometry_fingerprint


@pytest.mark.parametrize('use_ai', [False, True])
def test_all_adaptations_converge_to_previous_fail(plans, monkeypatch, use_ai):
    raw = DesignResult.model_validate_json(plans[0].layout_json)
    raw.entrances[0].offset += 0.25
    converges = replace(plans[0], layout_json=raw.model_dump_json())
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: [converges])
    if use_ai:
        provider_for(monkeypatch, [converges])
    with pytest.raises(GenerationFailure, match=generation.NO_DISTINCT_LAYOUT) as error:
        generate(previous_design(plans[0]))
    assert any(f.get('reason') == 'previous_geometry_repeated' for f in error.value.failures)


def test_fallback_searches_beyond_seven_plan_shortlist(plans, monkeypatch):
    converging = []
    for index in range(8):
        raw = DesignResult.model_validate_json(plans[0].layout_json)
        raw.entrances[0].offset += (index + 1) / 10
        converging.append(replace(plans[0], plan_code=f'A{index}', layout_json=raw.model_dump_json()))
    pool = [*converging, plans[2]]
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: pool)
    provider = provider_for(monkeypatch, pool, selected='A0')
    result = generate(previous_design(plans[0]))
    prompt = json.loads(provider.generate_json.call_args.args[1])
    assert len(prompt['candidate_plans']) == 7
    assert 'B' not in [p['plan_code'] for p in prompt['candidate_plans']]
    assert result.candidate_summary['selected_plan_code'] == 'B'
    assert result.geometry_fingerprint != plans[0].geometry_fingerprint


def test_shortlist_preserves_best_ranked_representative_and_families(plans, monkeypatch):
    second = replace(plans[2], plan_code='SECOND')
    third_layout = DesignResult.model_validate_json(plans[2].layout_json)
    third_layout.entrances[0].offset += 0.25
    other_family = replace(second, plan_code='OTHER', topology_family='CENTRAL_CORE',
                           layout_json=third_layout.model_dump_json())
    ranked = [plans[0], plans[1], second, other_family]
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: ranked)
    monkeypatch.setattr(generation, 'rank_base_plans', lambda *_: ranked)
    req, plot = generation.prepare_inputs(30, 'flat', PREFERENCES, PLOT)
    assert [p.plan_code for p in generation._candidate_pool(req, plot)] == ['A', 'OTHER', 'SECOND']


def test_fingerprint_ignores_order_ids_and_metadata(plans):
    original = DesignResult.model_validate_json(plans[0].layout_json)
    changed = original.model_copy(deep=True)
    ids = {r.room_id: f'renamed-{index}' for index, r in enumerate(changed.rooms)}
    for room in changed.rooms:
        room.room_id = ids[room.room_id]
        room.name = 'New display name'
    for connection in changed.connections:
        connection.from_room, connection.to_room = ids[connection.to_room], ids[connection.from_room]
    for entrance in changed.entrances:
        entrance.room_id = ids[entrance.room_id]
    changed.rooms.reverse()
    changed.connections.reverse()
    changed.entrances.reverse()
    changed.template_id = 'OTHER-CODE'
    changed.template_family = 'OTHER-LABEL'
    changed.foundation_type = 'pile'
    changed.terrain_type = 'coastal'
    changed.candidate_summary = {'name': 'Other name', 'designCode': 'OTHER'}
    assert geometry_fingerprint(changed) == geometry_fingerprint(original)


@pytest.mark.parametrize('field', ['room_type', 'floor', 'x', 'y', 'width', 'length'])
def test_fingerprint_preserves_room_geometry(plans, field):
    design = DesignResult.model_validate_json(plans[0].layout_json)
    before = geometry_fingerprint(design)
    room = design.rooms[0]
    setattr(room, field, 'study' if field == 'room_type' else getattr(room, field) + 1)
    assert geometry_fingerprint(design) != before


@pytest.mark.parametrize('change', ['edge', 'kind', 'entrance_room', 'wall', 'offset', 'width', 'mirror', 'rotation'])
def test_fingerprint_preserves_topology_and_orientation(plans, change):
    design = DesignResult.model_validate_json(plans[0].layout_json)
    before = geometry_fingerprint(design)
    if change == 'edge':
        design.connections.pop()
    elif change == 'kind':
        design.connections[0].kind = 'open'
    elif change == 'entrance_room':
        design.entrances[0].room_id = design.rooms[1].room_id
    elif change in ('wall', 'offset', 'width'):
        entrance = design.entrances[0]
        setattr(entrance, change, 'north' if change == 'wall' else getattr(entrance, change) + 0.0001)
    elif change == 'mirror':
        design = transform_design(design, mirror_horizontal=True)
    else:
        design = transform_design(design, rotation_degrees=90)
    assert geometry_fingerprint(design) != before


def test_ordinary_revision_may_preserve_geometry(plans, monkeypatch):
    monkeypatch.setattr(generation, 'filter_compatible_base_plans', lambda *_: list(plans[:2]))
    result = generate(previous_design(plans[0]), reason='Keep this arrangement')
    assert result.geometry_fingerprint == plans[0].geometry_fingerprint


def test_novelty_does_not_require_previous_plan_code(plans):
    previous = previous_design(plans[0])
    previous['candidate_summary'] = {}
    result = generate(previous)
    assert result.geometry_fingerprint != plans[0].geometry_fingerprint


@pytest.mark.parametrize('previous', [None, {}, {'floor_count': 1}])
def test_novelty_requires_valid_previous_geometry(plans, previous):
    with pytest.raises(GenerationFailure, match='Cannot compare geometry'):
        generation.generate_layout(30, 'flat', PREFERENCES, previous_design=previous,
                                   revision_reason='Generate Another', plot_constraints=PLOT)


def test_fingerprint_normalizes_numbers_without_rounding_geometry(plans):
    design = DesignResult.model_validate_json(plans[0].layout_json)
    before = geometry_fingerprint(design)
    design.rooms[0].x = -0.0
    design.rooms[0].width = int(design.rooms[0].width)
    assert geometry_fingerprint(design) == before
    design.rooms[0].width += 0.0001
    assert geometry_fingerprint(design) != before
