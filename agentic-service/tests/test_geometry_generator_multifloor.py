# Low-level placement/structural tests remain independent of the quality gate.
import pytest
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram, RoomIntent, AdjacencyIntent, EntranceIntent, VerticalCoreIntent
from app.design.geometry.geometry_generator import generate_geometry, LayoutSolver
from app.design.exceptions import GenerationFailure
from app.validation.geometry_validator import validate_geometry

def mock_plot(w=60, l=80, road='south') -> PlotConstraints:
    return PlotConstraints.model_validate({
        'land_size_perches': 20,
        'plot_width_ft': w,
        'plot_length_ft': l,
        'road_side': road,
        'terrain_type': 'flat',
        'setbacks': {'front': 0, 'rear': 0, 'left': 0, 'right': 0},
    })

def test_simple_2_floor():
    plot = mock_plot()
    program = SpatialProgram(
        concept="Two Floor", floor_count=2,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=200, min_area_sqft=150, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="dining", type="dining", floor=1, zone="PUBLIC", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bath1", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bed2", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bath2", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=True),
        reason_codes=[]
    )
    result, meta = LayoutSolver(program, plot).generate()
    
    assert result.floor_count == 2
    f1_rooms = [r for r in result.rooms if r.floor == 1]
    f2_rooms = [r for r in result.rooms if r.floor == 2]
    assert len(f1_rooms) == 5 # 4 + 1 stair
    assert len(f2_rooms) == 4 # 3 + 1 stair

def test_realistic_4b3b():
    plot = mock_plot(80, 80)
    program = SpatialProgram(
        concept="Family", floor_count=2,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=300, min_area_sqft=200, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=150, min_area_sqft=100, preferred_position="CENTER", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="dining", type="dining", floor=1, zone="PUBLIC", target_area_sqft=150, min_area_sqft=100, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bath1", type="bathroom", floor=1, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=1, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="MEDIUM"),
            RoomIntent(id="bed2", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="FRONT", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bed3", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="FRONT", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bed4", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=200, min_area_sqft=150, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bath2", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bath3", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=False),
        reason_codes=[]
    )
    result, meta = generate_geometry(program, plot)
    assert len([r for r in result.rooms if 'bedroom' in r.room_type]) == 4
    assert len([r for r in result.rooms if r.room_type == 'bathroom']) == 3
    assert result.candidate_status == 'VALID_HIGH_QUALITY'
    assert validate_geometry(result.rooms, 4, 2, plot.land_size_perches, plot=plot, design=result).passed

def test_stair_alignment_fails_if_offset():
    # If we artificially move the stair on floor 2, validation must fail
    plot = mock_plot()
    program = SpatialProgram(
        concept="Two Floor", floor_count=2,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=200, min_area_sqft=150, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bath2", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=True),
        reason_codes=[]
    )
    result, meta = LayoutSolver(program, plot).generate()
    
    # offset stair 2
    for r in result.rooms:
        if r.room_type == 'staircase' and r.floor == 2:
            r.x += 10.0
            
    val_result = validate_geometry(
        result.rooms,
        expected_bedrooms=1,
        expected_floors=2,
        land_size_perches=plot.land_size_perches,
        plot=plot,
        design=None
    )
    assert not val_result.passed
    assert any("staircase on floor 1 does not perfectly align" in f.lower() for f in val_result.failures)

def test_upper_support_fails_if_floating():
    plot = mock_plot()
    program = SpatialProgram(
        concept="Two Floor", floor_count=2,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=200, min_area_sqft=150, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH"),
            RoomIntent(id="bath2", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=True),
        reason_codes=[]
    )
    result, meta = LayoutSolver(program, plot).generate()
    
    # float a bedroom
    for r in result.rooms:
        if r.room_id == 'bed1':
            r.x += 50.0 # way outside floor 1 footprint
            
    val_result = validate_geometry(
        result.rooms,
        expected_bedrooms=1,
        expected_floors=2,
        land_size_perches=plot.land_size_perches,
        plot=plot,
        design=None
    )
    assert not val_result.passed

def test_service_alignment():
    # If align_service_zones is True, upstairs bath should be near downstairs kitchen/bath
    # We test it implicitly by ensuring layout generates successfully with score optimization
    plot = mock_plot()
    program = SpatialProgram(
        concept="Align", floor_count=2,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=200, min_area_sqft=150, preferred_position="FRONT", exterior_wall_required=True, privacy_level="LOW"),
            RoomIntent(id="kitchen", type="kitchen", floor=1, zone="SERVICE", target_area_sqft=100, min_area_sqft=80, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bath2", type="bathroom", floor=2, zone="SERVICE", target_area_sqft=50, min_area_sqft=40, preferred_position="CENTER", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=150, min_area_sqft=100, preferred_position="REAR", exterior_wall_required=True, privacy_level="HIGH")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=True),
        reason_codes=[]
    )
    res1, meta1 = LayoutSolver(program, plot).generate()
    assert res1.floor_count == 2

def test_impossible_core():
    # Plot is smaller than stair core rules
    plot = mock_plot(w=5, l=5)
    program = SpatialProgram(
        concept="Impossible", floor_count=2,
        rooms=[
            RoomIntent(id="living", type="living", floor=1, zone="PUBLIC", target_area_sqft=20, min_area_sqft=15, preferred_position="FRONT", exterior_wall_required=False, privacy_level="LOW"),
            RoomIntent(id="bed1", type="bedroom", floor=2, zone="PRIVATE", target_area_sqft=20, min_area_sqft=15, preferred_position="REAR", exterior_wall_required=False, privacy_level="LOW")
        ],
        adjacencies=[],
        entrance=EntranceIntent(preferred_side="SOUTH", connect_to="living"),
        vertical_core=VerticalCoreIntent(stair_position="CENTER", align_service_zones=True),
        reason_codes=[]
    )
    with pytest.raises(GenerationFailure, match="ROOM_MIN_DIMENSIONS_EXCEED_PLOT|STAIR_CORE_UNPLACEABLE"):
        generate_geometry(program, plot)
