from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.program.models import Requirements
from app.design.geometry.plot_constraints import PlotConstraints
from app.schemas.design_result import DesignResult, Entrance, RoomLayout


def test_bad_plan_regression_is_rejected():
    # Construct a layout that mimics the "screenshot-style failure"
    # - extremely long hallway/circulation spine
    # - bedrooms stacked like cells along one side
    # - bathrooms pushed to the far end
    # - living room and kitchen disconnected from the rest of the house
    # - fake L-shape

    rooms = [
        RoomLayout(room_id="living", room_type="living_room", floor=1, x=0, y=0, width=15, length=15),
        RoomLayout(room_id="dining", room_type="dining", floor=1, x=15, y=0, width=15, length=15),
        RoomLayout(room_id="kitchen", room_type="kitchen", floor=1, x=30, y=0, width=15, length=15),
        # A massive hallway that goes all the way down
        RoomLayout(room_id="hallway_1", room_type="hallway", floor=1, x=0, y=15, width=4, length=60),
        # Bedrooms stacked down one side of the hallway
        RoomLayout(room_id="bed_1", room_type="bedroom_1", floor=1, x=4, y=15, width=12, length=15),
        RoomLayout(room_id="bed_2", room_type="bedroom_2", floor=1, x=4, y=30, width=12, length=15),
        RoomLayout(room_id="bed_3", room_type="bedroom_3", floor=1, x=4, y=45, width=12, length=15),
        # Bathrooms pushed to the far end
        RoomLayout(room_id="bath_1", room_type="bathroom_1", floor=1, x=4, y=60, width=12, length=8),
        RoomLayout(room_id="bath_2", room_type="bathroom_2", floor=1, x=4, y=68, width=12, length=7),
    ]

    connections = [
        {"from_room": "living", "to_room": "dining", "kind": "open"},
        {"from_room": "dining", "to_room": "kitchen", "kind": "open"},
        {"from_room": "living", "to_room": "hallway_1", "kind": "door"},
        {"from_room": "hallway_1", "to_room": "bed_1", "kind": "door"},
        {"from_room": "hallway_1", "to_room": "bed_2", "kind": "door"},
        {"from_room": "hallway_1", "to_room": "bed_3", "kind": "door"},
        {"from_room": "hallway_1", "to_room": "bath_1", "kind": "door"},
        {"from_room": "hallway_1", "to_room": "bath_2", "kind": "door"},
    ]

    design = DesignResult(
        design_id="test_bad_plan",
        floor_count=1,
        total_built_up_area_sqft=sum(r.width * r.length for r in rooms),
        ground_footprint_sqft=sum(r.width * r.length for r in rooms),
        foundation_type="slab",
        terrain_type="flat",
        template_id="L_SHAPE",  # Claims to be L-Shape but is actually weird
        template_family="L_SHAPE",
        rooms=rooms,
        connections=connections,
        entrances=[Entrance(room_id="living", wall="south", offset=7.5)]
    )

    req = Requirements(bedrooms=3, bathrooms=2, floors=1, style="Modern Minimalist")
    plot = PlotConstraints.model_validate({
        'land_size_perches': 20,
        'plot_width_ft': 60.0,
        'plot_length_ft': 100.0,
        'road_side': 'south',
        'terrain_type': 'flat'
    })

    quality = validate_architectural_quality(design, req=req, plot=plot)

    assert not quality.passed, "Bad plan should be rejected!"
    assert any("hallway" in f.lower() or "circulation" in f.lower() for f in quality.failures), "Should be rejected due to circulation/hallways"
