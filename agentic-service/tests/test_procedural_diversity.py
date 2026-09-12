import pytest
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.candidate_generator import select_best, geometry_fingerprint

def test_multiple_seeds_produce_layout_diversity():
    req_dict = {
        "bedrooms": 3,
        "floors": 1,
        "style": "modern"
    }
    
    plot_dict = {
        "land_size_perches": 12.0,
        "terrain_type": "flat",
        "road_side": "south"
    }
    
    fingerprints = set()
    
    for seed in range(1, 11):
        req = Requirements.model_validate({**req_dict, "design_seed": seed})
        plot = PlotConstraints.model_validate(plot_dict)
        
        design = select_best(req, plot)
        
        # Verify valid counts
        assert len(design.rooms) > 0
        
        fp = geometry_fingerprint(design)
        fingerprints.add(fp)

    # We should get at least 3 different diverse layouts from 10 different seeds
    # for a standard flat 3-bedroom case
    assert len(fingerprints) >= 3, f"Expected at least 3 distinct layouts, got {len(fingerprints)}"

def test_same_seed_is_reproducible():
    req_dict = {
        "bedrooms": 3,
        "floors": 1,
        "style": "modern",
        "design_seed": 42
    }
    
    plot_dict = {
        "land_size_perches": 12.0,
        "terrain_type": "flat",
        "road_side": "south"
    }
    
    req1 = Requirements.model_validate(req_dict)
    plot1 = PlotConstraints.model_validate(plot_dict)
    design1 = select_best(req1, plot1)
    
    req2 = Requirements.model_validate(req_dict)
    plot2 = PlotConstraints.model_validate(plot_dict)
    design2 = select_best(req2, plot2)
    
    assert geometry_fingerprint(design1) == geometry_fingerprint(design2)
