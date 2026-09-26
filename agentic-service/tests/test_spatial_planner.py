from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram
from app.design.generation.spatial_planner import plan_spatial_program, _validate_spatial_program, _build_prompt
from app.design.exceptions import GenerationFailure

def mock_plot_constraints():
    return PlotConstraints.model_validate({
        'land_size_perches': 20,
        'plot_width_ft': 60,
        'plot_length_ft': 80,
        'road_side': 'south',
        'terrain_type': 'flat',
        'setbacks': {'front': 10, 'rear': 10, 'left': 5, 'right': 5},
    })

def mock_provider(json_response):
    provider = MagicMock()
    provider.provider_name = "mock"
    provider.model_name = "mock_model"
    provider.generate_json.return_value = json_response
    return provider


def test_single_floor_planning():
    req = Requirements(bedrooms=3, bathrooms=2, floors=1)
    plot = mock_plot_constraints()
    
    mock_resp = {
        "concept": "Simple 1-story",
        "floor_count": 1,
        "rooms": [
            {"id": "bed1", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed2", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR_LEFT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed3", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR_RIGHT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bath1", "type": "bathroom", "floor": 1, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "bath2", "type": "bathroom", "floor": 1, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "living", "type": "living", "floor": 1, "zone": "PUBLIC", "target_area_sqft": 250, "min_area_sqft": 200, "preferred_position": "FRONT", "exterior_wall_required": True, "privacy_level": "LOW"},
            {"id": "kitchen", "type": "kitchen", "floor": 1, "zone": "SERVICE", "target_area_sqft": 150, "min_area_sqft": 100, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "LOW"},
        ],
        "adjacencies": [
            {"room_a": "living", "room_b": "kitchen", "relationship": "ADJACENT", "priority": "HIGH"}
        ],
        "entrance": {"preferred_side": "SOUTH", "connect_to": "living"},
        "vertical_core": None,
        "reason_codes": ["PUBLIC_FRONT"]
    }
    
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(mock_resp)
        program, meta = plan_spatial_program(req, plot)
        
        assert program.floor_count == 1
        assert len([r for r in program.rooms if "bedroom" in r.type]) == 3
        assert len([r for r in program.rooms if "bathroom" in r.type]) == 2
        assert meta["total_target_area"] == sum(r.target_area_sqft for r in program.rooms)


def test_multi_floor_planning():
    req = Requirements(bedrooms=4, bathrooms=3, floors=2)
    plot = mock_plot_constraints()
    
    mock_resp = {
        "concept": "2-story family",
        "floor_count": 2,
        "rooms": [
            {"id": "bed1", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed2", "type": "bedroom", "floor": 2, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR_LEFT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed3", "type": "bedroom", "floor": 2, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR_RIGHT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed4", "type": "bedroom", "floor": 2, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "FRONT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bath1", "type": "bathroom", "floor": 1, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "bath2", "type": "bathroom", "floor": 2, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "bath3", "type": "bathroom", "floor": 2, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "living", "type": "living", "floor": 1, "zone": "PUBLIC", "target_area_sqft": 250, "min_area_sqft": 200, "preferred_position": "FRONT", "exterior_wall_required": True, "privacy_level": "LOW"},
            {"id": "kitchen", "type": "kitchen", "floor": 1, "zone": "SERVICE", "target_area_sqft": 150, "min_area_sqft": 100, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "LOW"},
        ],
        "adjacencies": [],
        "entrance": {"preferred_side": "SOUTH", "connect_to": "living"},
        "vertical_core": {"stair_position": "CENTER", "align_service_zones": True},
        "reason_codes": []
    }
    
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(mock_resp)
        program, meta = plan_spatial_program(req, plot)
        
        assert program.floor_count == 2
        assert len([r for r in program.rooms if "bedroom" in r.type]) == 4
        assert len(set(r.floor for r in program.rooms if "bedroom" in r.type)) == 2
        assert program.vertical_core is not None


def test_invalid_gpt_output():
    req = Requirements(bedrooms=3, bathrooms=2, floors=1)
    plot = mock_plot_constraints()
    
    # Base valid structure
    base_resp = {
        "concept": "Simple",
        "floor_count": 1,
        "rooms": [
            {"id": "bed1", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed2", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR_LEFT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bed3", "type": "bedroom", "floor": 1, "zone": "PRIVATE", "target_area_sqft": 150, "min_area_sqft": 120, "preferred_position": "REAR_RIGHT", "exterior_wall_required": True, "privacy_level": "HIGH"},
            {"id": "bath1", "type": "bathroom", "floor": 1, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "bath2", "type": "bathroom", "floor": 1, "zone": "SERVICE", "target_area_sqft": 50, "min_area_sqft": 40, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "HIGH"},
            {"id": "living", "type": "living", "floor": 1, "zone": "PUBLIC", "target_area_sqft": 250, "min_area_sqft": 200, "preferred_position": "FRONT", "exterior_wall_required": True, "privacy_level": "LOW"},
            {"id": "kitchen", "type": "kitchen", "floor": 1, "zone": "SERVICE", "target_area_sqft": 150, "min_area_sqft": 100, "preferred_position": "CENTER", "exterior_wall_required": False, "privacy_level": "LOW"},
        ],
        "adjacencies": [],
        "entrance": {"preferred_side": "SOUTH", "connect_to": "living"},
        "vertical_core": None,
        "reason_codes": []
    }
    
    # 1. Missing bedroom
    resp = dict(base_resp)
    resp["rooms"] = resp["rooms"][1:] # removes bed1
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(resp)
        with pytest.raises(GenerationFailure, match="Expected 3 bedrooms"):
            plan_spatial_program(req, plot)
            
    # 2. Duplicate room ID
    resp = dict(base_resp)
    resp["rooms"] = list(base_resp["rooms"])
    resp["rooms"][0] = dict(resp["rooms"][1])
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(resp)
        with pytest.raises(GenerationFailure, match="Duplicate room ID"):
            plan_spatial_program(req, plot)
            
    # Let's test adjacency to nonexistent room
    resp = dict(base_resp)
    resp["adjacencies"] = [{"room_a": "living", "room_b": "GHOST", "relationship": "ADJACENT", "priority": "HIGH"}]
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(resp)
        with pytest.raises(GenerationFailure, match="references unknown room"):
            plan_spatial_program(req, plot)
            
    # Negative area (caught by pydantic)
    resp = dict(base_resp)
    resp["rooms"] = list(base_resp["rooms"])
    resp["rooms"][0] = dict(resp["rooms"][0])
    resp["rooms"][0]["target_area_sqft"] = -50
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(resp)
        with pytest.raises(GenerationFailure): # Pydantic ValidationError wrapped in GenerationFailure
            plan_spatial_program(req, plot)
            
    # Program area exceeds budget
    resp = dict(base_resp)
    resp["rooms"] = list(base_resp["rooms"])
    resp["rooms"][0] = dict(resp["rooms"][0])
    resp["rooms"][0]["target_area_sqft"] = 1900
    resp["rooms"][1] = dict(resp["rooms"][1])
    resp["rooms"][1]["target_area_sqft"] = 1900
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(resp)
        with pytest.raises(GenerationFailure, match="exceeds budget"):
            plan_spatial_program(req, plot)
            
    # Invalid Enum (caught by pydantic)
    resp = dict(base_resp)
    resp["rooms"] = list(base_resp["rooms"])
    resp["rooms"][0] = dict(resp["rooms"][0])
    resp["rooms"][0]["zone"] = "FAKE_ZONE"
    with patch("app.design.generation.spatial_planner.get_available_design_provider") as get_prov:
        get_prov.return_value = mock_provider(resp)
        with pytest.raises(GenerationFailure):
            plan_spatial_program(req, plot)


def test_token_safety():
    req = Requirements(bedrooms=3, bathrooms=2, floors=1)
    plot = mock_plot_constraints()
    
    prompt = _build_prompt(req, plot, 1500)
    
    # Should not contain large lists or catalogue references
    assert "pre-designed-plans.json" not in prompt
    assert "LayoutJson" not in prompt
    
    prompt_chars = len(prompt)
    assert prompt_chars < 600  # Should be very compact
