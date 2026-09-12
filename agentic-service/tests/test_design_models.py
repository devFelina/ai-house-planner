import pytest
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints, Setbacks
from app.design.spatial_program import build_program
from app.design.topology_registry import eligible_topologies


def test_estimated_plot_and_distinct_area_caps():
    p = PlotConstraints(land_size_perches=15)
    assert p.dimensions_estimated
    assert p.plot_width_ft * p.plot_length_ft == pytest.approx(15 * 272.25)
    assert p.maximum_ground_footprint <= p.maximum_total_floor_area
    assert len(p.buildable_polygon) == 4


def test_road_relative_setbacks():
    p = PlotConstraints(land_size_perches=15, plot_width_ft=45, plot_length_ft=90, road_side='east')
    assert p.buildable_width == 28
    assert p.buildable_length == 80
    assert not p.dimensions_estimated


def test_impossible_setbacks_rejected():
    with pytest.raises(ValueError):
        PlotConstraints(land_size_perches=1, plot_width_ft=10, plot_length_ft=10)


def test_floor_program_does_not_duplicate_bedrooms():
    p = build_program(Requirements(bedrooms=3, floors=2))
    assert sum(r.room_type.startswith('bedroom') for r in p.rooms) == 3
    assert {r.floor for r in p.rooms if r.zone == 'public'} == {1}
    assert {r.floor for r in p.rooms if r.room_type.startswith('bedroom')} == {2}


def test_topology_registry_is_geography_sensitive():
    r = Requirements(floors=1)
    wide = eligible_topologies(r, PlotConstraints(land_size_perches=30, plot_width_ft=90, plot_length_ft=90))
    narrow = eligible_topologies(r, PlotConstraints(land_size_perches=30, plot_width_ft=26, plot_length_ft=200))
    assert len(wide) >= 3
    assert [t.name for t in narrow] == ['LINEAR']
