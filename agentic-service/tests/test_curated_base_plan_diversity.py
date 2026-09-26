from collections import defaultdict

import pytest

from app.design.architectural_quality import validate_architectural_quality
from app.design.base_plan_library import load_base_plan_catalog
from app.design.diversity import geometry_fingerprint
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.room_counts import count_bathrooms
from app.schemas.design_result import DesignResult
from app.tools import layout_generation_tool as generation
from app.validation.geometry_validator import validate_geometry

TARGETS = ((3, 1, 1), (3, 2, 1), (4, 2, 2))
PREFIX = "HP-CURATED-"


def curated_records():
    load_base_plan_catalog.cache_clear()
    return [plan for plan in load_base_plan_catalog() if plan.plan_code.startswith(PREFIX)]


def test_curated_target_configurations_have_four_unique_valid_geometries():
    grouped = defaultdict(list)
    for plan in curated_records():
        grouped[(plan.bedrooms, plan.bathrooms, plan.floors)].append(plan)

    for configuration in TARGETS:
        plans = grouped[configuration]
        assert len(plans) == 4
        assert len({plan.geometry_fingerprint for plan in plans}) == 4
        assert len({plan.topology_family for plan in plans}) == 4

        for plan in plans:
            design = DesignResult.model_validate_json(plan.layout_json)
            bedrooms, bathrooms, floors = configuration
            assert count_bathrooms(design.rooms) == bathrooms
            assert len([room for room in design.rooms if "bedroom" in room.room_type]) == bedrooms
            assert {room.floor for room in design.rooms} == set(range(1, floors + 1))
            plot = PlotConstraints(land_size_perches=50, plot_width_ft=100,
                                   plot_length_ft=100, terrain_type="flat")
            assert validate_geometry(design.rooms, bedrooms, floors, 50,
                                     plot=plot, design=design).passed
            assert validate_architectural_quality(
                design, Requirements(bedrooms=bedrooms, bathrooms=bathrooms, floors=floors), plot
            ).passed


@pytest.mark.parametrize("configuration", TARGETS)
def test_generate_another_returns_a_distinct_curated_geometry(configuration, monkeypatch):
    bedrooms, bathrooms, floors = configuration
    target_plans = [plan for plan in curated_records()
                    if (plan.bedrooms, plan.bathrooms, plan.floors) == configuration]
    monkeypatch.setattr(generation, "get_available_design_provider", lambda: None)
    monkeypatch.setattr(generation, "filter_compatible_base_plans", lambda *_: target_plans)
    preferences = {"bedrooms": bedrooms, "bathrooms": bathrooms, "floors": floors,
                   "style": "Modern Minimalist"}
    plot = {"plot_width_ft": 100, "plot_length_ft": 100}
    previous = generation.generate_layout(50, "flat", preferences, plot_constraints=plot)
    alternate = generation.generate_layout(
        50, "flat", preferences, previous_design=previous.model_dump(),
        revision_reason="Generate Another", plot_constraints=plot)
    assert geometry_fingerprint(alternate) != geometry_fingerprint(previous)

