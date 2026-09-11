import pytest
from app.tools.layout_templates import select_template, ALL_TEMPLATES

def test_select_template_exact_match():
    # 3BR, 1F, flat -> TEMPLATE_3BR_1F_FLAT
    template = select_template(bedrooms=3, floors=1, terrain_type="flat")
    assert template.template_id == "3BR_1F_FLAT"

def test_select_template_fallback_terrain():
    # 3BR, 1F, unknown_terrain -> fallback to same BR/F
    template = select_template(bedrooms=3, floors=1, terrain_type="unknown")
    assert template.bedroom_count == 3
    assert template.floor_count == 1
    assert template.template_id == "3BR_1F_FLAT" # first one

def test_select_template_fallback_closest_bedrooms():
    # 5BR, 2F, flat -> no exact match, falls back to 4BR 2F Flat
    template = select_template(bedrooms=5, floors=2, terrain_type="flat")
    assert template.floor_count == 2
    assert template.bedroom_count == 4 # closest to 5

def test_all_templates_have_unique_ids():
    ids = [t.template_id for t in ALL_TEMPLATES]
    assert len(ids) == len(set(ids))

def test_all_templates_have_valid_rooms():
    for template in ALL_TEMPLATES:
        assert len(template.rooms) > 0
        for room in template.rooms:
            assert room.width > 0
            assert room.length > 0
            assert room.floor >= 1
