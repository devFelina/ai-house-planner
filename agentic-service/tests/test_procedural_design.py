from unittest.mock import patch
import pytest
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.candidate_generator import generate_candidates, select_best, GenerationFailure
from app.tools.geometry_validator import validate_geometry


def make(terrain='flat', **preferences):
    req = Requirements(floors=preferences.pop('floors', 1), design_seed=preferences.pop('design_seed', 123), **preferences)
    plot = PlotConstraints(land_size_perches=30, plot_width_ft=90, plot_length_ft=90, terrain_type=terrain)
    return req, plot


def validate(design, req, plot):
    return validate_geometry(design.rooms, req.bedrooms, req.floors, plot.land_size_perches, plot=plot, design=design)


def test_at_least_three_distinct_valid_geometries():
    req, plot = make()
    candidates, _ = generate_candidates(req, plot)
    assert len({c.template_family for c in candidates}) >= 3
    shapes = set()
    for c in candidates:
        assert validate(c, req, plot).passed
        shapes.add(tuple(sorted((r.floor, r.x, r.y, r.width, r.length) for r in c.rooms)))
    assert len(shapes) >= 3


def test_narrow_plot_selects_linear():
    req, _ = make()
    plot = PlotConstraints(land_size_perches=30, plot_width_ft=26, plot_length_ft=200)
    result = select_best(req, plot)
    assert result.template_family == 'LINEAR'
    assert validate(result, req, plot).passed


@pytest.mark.parametrize('floors', [1, 2, 3])
@pytest.mark.parametrize('bedrooms', [1, 3, 5])
def test_exact_bedrooms_floor_use_and_bounds(floors, bedrooms):
    req, plot = make(floors=floors, bedrooms=bedrooms)
    result = select_best(req, plot)
    assert len([r for r in result.rooms if r.room_type.startswith('bedroom')]) == bedrooms
    assert {r.floor for r in result.rooms} == set(range(1, floors+1))
    assert validate(result, req, plot).passed
    assert all(0 <= r.x < r.x+r.width <= plot.buildable_width+0.001 for r in result.rooms)
    assert all(0 <= r.y < r.y+r.length <= plot.buildable_length+0.001 for r in result.rooms)
    if floors > 1:
        assert any(c.kind == 'stair' for c in result.connections)
        assert all(r.floor == 1 for r in result.rooms if r.room_type in ('living_room', 'kitchen'))


def test_same_seed_same_full_candidates():
    req, plot = make()
    a, rejected_a = generate_candidates(req, plot)
    b, rejected_b = generate_candidates(req, plot)
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]
    assert rejected_a == rejected_b


def test_different_seed_changes_valid_geometry():
    req, plot = make()
    a = select_best(req, plot)
    b = select_best(req.model_copy(update={'design_seed': 456}), plot)
    assert [(r.x, r.y, r.width, r.length) for r in a.rooms] != [(r.x, r.y, r.width, r.length) for r in b.rooms]
    assert validate(b, req, plot).passed


@pytest.mark.parametrize('damage,rule', [('overlap','room_overlap'), ('disconnected','disconnected_layout'),
    ('bounds','building_bounds'), ('duplicate','duplicate_room_id'), ('connections','accessibility'),
    ('stairs','stair_requirement'), ('area','area_mismatch'), ('door','opening_bounds')])
def test_invalid_geometry_fails_closed(damage, rule):
    req, plot = make(floors=2)
    result = select_best(req, plot)
    if damage == 'overlap':
        a, b = [r for r in result.rooms if r.floor == 1][:2]
        a.x, a.y = b.x, b.y
    elif damage == 'disconnected':
        result.rooms[0].x += 40
    elif damage == 'bounds':
        result.rooms[0].x = plot.buildable_width
    elif damage == 'duplicate':
        result.rooms[0].room_id = result.rooms[1].room_id
    elif damage == 'connections':
        result.connections = []
    elif damage == 'stairs':
        next(r for r in result.rooms if r.room_type == 'staircase' and r.floor == 2).x += 2
    elif damage == 'area':
        result.total_built_up_area_sqft += 100
    elif damage == 'door':
        result.rooms[0].doors[0].offset = 1000
    checked = validate(result, req, plot)
    assert not checked.passed
    assert rule in checked.failed_rules


def test_all_candidates_invalid_is_failure():
    with patch('app.design.candidate_generator.generate_geometry', side_effect=ValueError('invalid geometry')):
        with pytest.raises(GenerationFailure):
            select_best(*make())


def test_terrain_changes_conceptual_topology():
    flat = select_best(*make())
    hill = select_best(*make(terrain='hillside'))
    assert flat.template_family != hill.template_family
    assert hill.template_family == 'HILLSIDE_STEPPED'
    assert hill.foundation_type == 'stepped'


def test_validator_rejects_terrain_foundation_mismatch():
    req, plot = make(terrain='coastal')
    result = select_best(req, plot)
    result.foundation_type = 'slab'
    checked = validate(result, req, plot)
    assert not checked.passed
    assert 'terrain_foundation' in checked.failed_rules


@pytest.mark.parametrize('preferences', [dict(open_plan=True), dict(dining_required=True),
    dict(master_bedroom=True, attached_bathroom=True), dict(home_office=True),
    dict(accessibility=True), dict(floors=2, balcony=True), dict(bathrooms=3)])
def test_preferences_produce_valid_program(preferences):
    req, plot = make(**preferences)
    result = select_best(req, plot)
    assert validate(result, req, plot).passed
    kinds = {r.room_type for r in result.rooms}
    for preference, kind in [('open_plan','dining'),('dining_required','dining'),('attached_bathroom','bathroom_attached'),('home_office','home_office'),('balcony','balcony')]:
        if preferences.get(preference):
            assert kind in kinds


def test_preferences_change_selected_concept():
    conventional = select_best(*make())
    garden = select_best(*make(garden_priority=True))
    open_plan = select_best(*make(open_plan=True))
    assert len({conventional.template_family, garden.template_family, open_plan.template_family}) >= 2


@pytest.mark.parametrize('side', ['south', 'north', 'east', 'west'])
def test_road_side_orients_entrance(side):
    req, plot = make()
    plot = PlotConstraints.model_validate({**plot.model_dump(), 'road_side': side})
    result = select_best(req, plot)
    assert result.entrances[0].wall == side
    assert validate(result, req, plot).passed


def test_score_selects_best_not_candidate_one():
    req, plot = make()
    candidates, rejected = generate_candidates(req, plot)
    candidates.sort(key=lambda c: c.design_score)  # Worst valid candidate arrives first.
    with patch('app.design.candidate_generator.generate_candidates', return_value=(candidates, rejected)):
        result = select_best(req, plot)
    assert result.design_score == max(c.design_score for c in candidates)
    assert result.design_id != candidates[0].design_id
