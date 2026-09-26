"""Selection tests for site and preference suitability, without a live provider."""
from dataclasses import replace

from app.design.catalogue.base_plan_library import (
    filter_compatible_base_plans,
    load_base_plan_catalog,
    rank_base_plans,
)
from app.design.catalogue.plan_suitability import SUITABILITY_WEIGHTS, suitability_breakdown
from app.design.generation import generation_service as generation
from app.design.generation.generation_service import _candidate_pool, prepare_inputs


def ranked(land, preferences, dimensions):
    req, plot = prepare_inputs(land, 'flat', preferences, dimensions)
    plans = rank_base_plans(filter_compatible_base_plans(req, plot), req, plot)
    return req, plot, plans


def curated(plans, config):
    return [plan for plan in plans if (plan.bedrooms, plan.bathrooms, plan.floors) == config
            and plan.plan_code.startswith('HP-CURATED-')]


def test_suitability_weights_are_centralized_and_balanced():
    assert sum(SUITABILITY_WEIGHTS.values()) == 100
    assert max(SUITABILITY_WEIGHTS.values()) <= 20


def test_narrow_plot_ranks_linear_first():
    _, _, plans = ranked(20, {'bedrooms': 3, 'bathrooms': 2, 'floors': 1},
                         {'plot_width_ft': 50, 'plot_length_ft': 110})
    assert plans[0].topology_family == 'LINEAR'


def test_wide_balanced_plot_moves_non_linear_topologies_ahead():
    _, _, plans = ranked(20, {'bedrooms': 3, 'bathrooms': 2, 'floors': 1},
                         {'plot_width_ft': 90, 'plot_length_ft': 65})
    assert plans[0].topology_family in {'SPLIT_ZONE', 'CENTRAL_CORE', 'COMPACT_RECTANGLE'}
    assert all(plan.topology_family != 'LINEAR' for plan in plans[:3])


def test_space_priorities_change_curated_ranking():
    dimensions = {'plot_width_ft': 95, 'plot_length_ft': 70}
    _, _, garden = ranked(24, {'bedrooms': 3, 'bathrooms': 1, 'floors': 1,
                               'space_priority': 'outdoor_garden'}, dimensions)
    _, _, compact = ranked(24, {'bedrooms': 3, 'bathrooms': 1, 'floors': 1,
                                'space_priority': 'compact_cost_efficient'}, dimensions)
    assert curated(garden, (3, 1, 1))[0].topology_family == 'L_SHAPE'
    assert curated(compact, (3, 1, 1))[0].topology_family == 'COMPACT_RECTANGLE'


def test_accessibility_changes_score_using_ground_floor_program():
    dimensions = {'plot_width_ft': 90, 'plot_length_ft': 91}
    req, plot, plans = ranked(30, {'bedrooms': 4, 'bathrooms': 2, 'floors': 2,
                                   'accessibility': True}, dimensions)
    scores = [suitability_breakdown(plan, req, plot)['score'] for plan in plans]
    assert plans
    assert scores == sorted(scores, reverse=True)
    assert all(plan.capabilities['accessibility'] for plan in plans)
    assert any(plan.accessibility_score != plans[0].accessibility_score for plan in plans[1:])


def test_style_changes_ranking_and_score():
    dimensions = {'plot_width_ft': 95, 'plot_length_ft': 70}
    _, _, modern = ranked(24, {'bedrooms': 3, 'bathrooms': 1, 'floors': 1,
                               'style': 'Modern Minimalist'}, dimensions)
    _, _, tropical = ranked(24, {'bedrooms': 3, 'bathrooms': 1, 'floors': 1,
                                 'style': 'Tropical Modernism'}, dimensions)
    assert curated(modern, (3, 1, 1))[0].topology_family in {'CENTRAL_CORE', 'COMPACT_RECTANGLE'}
    assert curated(tropical, (3, 1, 1))[0].topology_family == 'L_SHAPE'


def test_unsupported_required_feature_is_filtered():
    req, plot = prepare_inputs(24, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1,
                                            'home_office': True},
                                    {'plot_width_ft': 95, 'plot_length_ft': 70})
    candidates = filter_compatible_base_plans(req, plot)
    assert all(plan.capabilities['home_office'] for plan in candidates)


def test_impossible_dimensions_are_filtered_before_shortlist(monkeypatch):
    source = next(plan for plan in load_base_plan_catalog()
                  if (plan.bedrooms, plan.bathrooms, plan.floors) == (3, 2, 1))
    req, plot = prepare_inputs(20, 'flat', {'bedrooms': 3, 'bathrooms': 2, 'floors': 1},
                                    {'plot_width_ft': 50, 'plot_length_ft': 110})
    # minimum_plot_width_ft is compared against plot.plot_width_ft (not buildable_width)
    impossible = replace(source, plan_code='TOO-WIDE', minimum_plot_width_ft=(plot.plot_width_ft or 0) + 1)
    import app.design.catalogue.base_plan_library as library
    monkeypatch.setattr(library, 'load_base_plan_catalog', lambda: [impossible])
    compatible = filter_compatible_base_plans(req, plot)
    assert compatible == []


def test_ai_metadata_contains_only_compact_selection_evidence():
    req, plot, _ = ranked(20, {'bedrooms': 3, 'bathrooms': 2, 'floors': 1},
                          {'plot_width_ft': 90, 'plot_length_ft': 65})
    from app.design.catalogue.base_plan_library import compact_plan_metadata
    payload = compact_plan_metadata(_candidate_pool(req, plot)[:2], req, plot)
    required = {'plan_code', 'topology_family', 'suitability_score', 'supported_features',
                'plot_fit', 'geometry_fingerprint'}
    assert all(set(item) == required for item in payload)
    assert all('layout_json' not in item and 'rooms' not in item for item in payload)


def test_generation_emits_bounded_workflow_observability(caplog, monkeypatch):
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: None)
    caplog.set_level('INFO', logger='app.design.generation.generation_service')
    result = generation.generate_layout(
        20, 'flat', {'bedrooms': 3, 'bathrooms': 2, 'floors': 1},
        plot_constraints={'plot_width_ft': 90, 'plot_length_ft': 65}, design_seed=7)
    messages = '\n'.join(record.getMessage() for record in caplog.records)
    for stage in ('[Design Input]', '[Candidate Filter]', '[Suitability Ranking]',
                  '[AI Selection]', '[Adaptation]', '[Validation]', '[Final Design]'):
        assert stage in messages
    assert result.geometry_fingerprint in messages
    assert '"rooms"' not in messages

def test_guided_ui_hard_parking_requirement_is_enforced(monkeypatch):
    req, plot = prepare_inputs(24, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1, 'parking': True}, {'plot_width_ft': 95, 'plot_length_ft': 70})
    candidates = filter_compatible_base_plans(req, plot)
    # The current catalogue has no parking-capable plans, so this should return []
    assert len(candidates) == 0

def test_guided_ui_hard_balcony_requirement_is_enforced(monkeypatch):
    req, plot = prepare_inputs(24, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1, 'balcony': True}, {'plot_width_ft': 95, 'plot_length_ft': 70})
    candidates = filter_compatible_base_plans(req, plot)
    # The current catalogue has no balcony-capable plans, so this should return []
    assert len(candidates) == 0

def test_narrow_plot_rejects_balanced_only_plans_if_footprint_does_not_fit():
    # C. NARROW plot + BALANCED-only plan whose footprint does not fit -> rejected
    # (Because we removed the blanket BALANCED->NARROW exception in the filter)
    req, plot = prepare_inputs(15, 'flat', {'bedrooms': 3, 'bathrooms': 2, 'floors': 1}, {'plot_width_ft': 30, 'plot_length_ft': 136})
    assert plot.plot_class.endswith('NARROW') or plot.plot_class.endswith('VERY_NARROW')
    candidates = filter_compatible_base_plans(req, plot)
    # The only compatible topologies should be ones that explicitly support NARROW (like LINEAR)
    assert all('NARROW' in plan.supported_plot_shapes for plan in candidates)

def test_total_plot_dims_pass_but_footprint_violates_buildable_envelope(monkeypatch):
    # D. Minimum total plot dims pass but footprint violates setback-adjusted buildable envelope -> rejected by geometry validation
    def test_total_plot_dims_pass_but_footprint_violates_buildable_envelope(monkeypatch):
        # D. Minimum total plot dims pass but footprint violates setback-adjusted buildable envelope -> rejected by filter
        from app.design.catalogue.base_plan_library import (
            filter_compatible_base_plans_with_diagnostics,
        )

        # 20 perches, wide and shallow. Total length 49ft (passes catalog minimums).
        # We use custom huge setbacks (front=20, rear=15) so buildable depth is only 14ft, causing footprint failure.
        req, plot = prepare_inputs(20, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1}, {'plot_width_ft': 110, 'plot_length_ft': 49})
        plot.setbacks.front = 20
        plot.setbacks.rear = 15
        candidates, diagnostics = filter_compatible_base_plans_with_diagnostics(req, plot)

        # The filter should reject plans because their footprint exceeds the buildable length
        # We expect 'footprint_length' to be in the diagnostics for rejected plans
        assert 'footprint_length' in diagnostics

        # Verify that no COMPACT_RECTANGLE plan makes it through
        assert not any(p for p in candidates if p.topology_family == 'COMPACT_RECTANGLE')

def test_missing_dimensions_uses_balanced_conceptual_shape():
    # E. Missing physical dimensions + BALANCED conceptual shape -> deterministic estimated dimensions
    _req, plot = prepare_inputs(10, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1}, {})
    assert plot.dimension_source == 'area_estimated'
    # Aspect ratio should be 1.25
    aspect = max(plot.plot_width_ft, plot.plot_length_ft) / min(plot.plot_width_ft, plot.plot_length_ft)
    assert abs(aspect - 1.25) < 0.01

def test_same_input_produces_same_estimated_dimensions():
    # F. Same input produces same estimated dimensions
    _req1, plot1 = prepare_inputs(10, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1}, {})
    _req2, plot2 = prepare_inputs(10, 'flat', {'bedrooms': 3, 'bathrooms': 1, 'floors': 1}, {})
    assert plot1.plot_width_ft == plot2.plot_width_ft
    assert plot1.plot_length_ft == plot2.plot_length_ft
