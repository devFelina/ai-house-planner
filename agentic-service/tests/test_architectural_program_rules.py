from copy import deepcopy

from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.catalogue.base_plan_library import load_base_plan_catalog
from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.room_rules import room_kind
from app.validation.geometry_validator import validate_geometry


def plan(floors):
    record = next(p for p in load_base_plan_catalog() if p.floors == floors and p.bedrooms >= 2)
    return deepcopy(record.design), record


def context(record, **requirements):
    req = Requirements(bedrooms=record.bedrooms, bathrooms=record.bathrooms,
                       floors=record.floors, **requirements)
    design = record.design
    width = max(r.x + r.width for r in design.rooms) + 20
    length = max(r.y + r.length for r in design.rooms) + 20
    plot = PlotConstraints(land_size_perches=40, plot_width_ft=width,
                           plot_length_ft=length, terrain_type=design.terrain_type)
    return req, plot


def failures(design, record, **requirements):
    req, plot = context(record, **requirements)
    return validate_architectural_quality(design, req, plot).failures


def test_single_floor_stair_is_rejected():
    design, record = plan(1)
    design.rooms[0].room_type = 'staircase'
    assert 'program_stair_forbidden_single_floor' in failures(design, record)
    req, plot = context(record)
    geometry = validate_geometry(design.rooms, req.bedrooms, 1, 40, plot=plot)
    assert 'stair_forbidden' in geometry.failed_rules


def test_two_floor_plan_without_stairs_is_rejected():
    design, record = plan(2)
    design.rooms = [r for r in design.rooms if room_kind(r.room_type) != 'staircase']
    assert 'program_stair_required' in failures(design, record)


def test_accessibility_requires_ground_floor_bed_and_bath():
    design, record = plan(2)
    for room in design.rooms:
        if room.floor == 1 and room_kind(room.room_type) in {'bedroom', 'bathroom'}:
            room.floor = 2
    assert 'preference_accessibility' in failures(design, record, accessibility=True)


def test_master_ensuite_requires_dedicated_direct_connection():
    design, record = plan(1)
    assert 'preference_master_ensuite' in failures(design, record, attached_bathroom=True)


def test_distinct_dining_and_office_are_required():
    design, record = plan(1)
    result = failures(design, record, dining_required=True, home_office=True)
    assert 'preference_dining' in result
    assert 'preference_home_office' in result


def test_balcony_on_single_floor_is_rejected():
    design, record = plan(1)
    design.rooms[-1].room_type = 'balcony'
    assert 'program_balcony' in failures(design, record, balcony=True)


def test_veranda_must_be_ground_floor_and_exterior():
    design, record = plan(2)
    design.rooms[-1].room_type = 'veranda'
    assert 'program_veranda' in failures(design, record, veranda=True)


def test_utility_requires_kitchen_service_relationship():
    design, record = plan(1)
    assert 'preference_utility' in failures(design, record, utility_room=True)


def test_parking_requires_real_site_geometry():
    design, record = plan(1)
    assert 'preference_parking' in failures(design, record, parking=True)
