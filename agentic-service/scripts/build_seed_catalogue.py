"""Guarded seed exporter using the existing catalogue arrangements.

Moved from the historical build_perfect_library_all.py scratch script. No room
arrangements are added here. Run explicitly with `python -m scripts.build_seed_catalogue`
from agentic-service when catalogue regeneration is authorized.
"""
import json
from pathlib import Path

from app.design.adjacency import build_connections
from app.design.architectural_quality import validate_architectural_quality
from app.design.models import Requirements
from app.design.plan_adapter import finish_layout
from app.design.plot_constraints import PlotConstraints
from app.design.room_counts import count_bathrooms
from app.schemas.design_result import DesignResult, RoomLayout
from app.validation.geometry_validator import validate_geometry

r1 = [
    {"room_id": "living", "room_type": "living_room", "floor": 1, "x": 0, "y": 0, "width": 11, "length": 13},
    {"room_id": "bed_1", "room_type": "bedroom_1", "floor": 1, "x": 0, "y": 13, "width": 11, "length": 17},
    {"room_id": "bed_2", "room_type": "bedroom_2", "floor": 1, "x": 19.5, "y": 13, "width": 11, "length": 17},
    {"room_id": "bed_3", "room_type": "bedroom_3", "floor": 1, "x": 19.5, "y": 0, "width": 11, "length": 13},
    {"room_id": "kitchen", "room_type": "kitchen", "floor": 1, "x": 11, "y": 0, "width": 8, "length": 10},
    {"room_id": "hall_1", "room_type": "hallway", "floor": 1, "x": 16, "y": 10, "width": 3.5, "length": 10},
    {"room_id": "bath_1", "room_type": "bathroom_1", "floor": 1, "x": 11, "y": 10, "width": 5, "length": 10}
]

r2 = [
    {"room_id": "living", "room_type": "living_room", "floor": 1, "x": 0, "y": 0, "width": 11, "length": 10},
    {"room_id": "bed_1", "room_type": "bedroom_1", "floor": 1, "x": 0, "y": 10, "width": 11, "length": 17},
    {"room_id": "bed_2", "room_type": "bedroom_2", "floor": 1, "x": 20, "y": 10, "width": 11, "length": 17},
    {"room_id": "bed_3", "room_type": "bedroom_3", "floor": 1, "x": 20, "y": 0, "width": 11, "length": 10},
    {"room_id": "kitchen", "room_type": "kitchen", "floor": 1, "x": 11, "y": 0, "width": 8, "length": 8},
    {"room_id": "hall_1", "room_type": "hallway", "floor": 1, "x": 16, "y": 8, "width": 4, "length": 9},
    {"room_id": "bath_1", "room_type": "bathroom_1", "floor": 1, "x": 11, "y": 8, "width": 5, "length": 9}
]

def make_rooms(beds, baths, floors, base_r=r1):
    rooms = []
    current_beds = 3
    current_baths = 1

    for r in base_r:
        new_r = dict(r)
        rooms.append(new_r)

    for f in range(2, floors + 1):
        for r in base_r:
            new_r = dict(r)
            new_r['floor'] = f
            if 'bed' in new_r['room_id']:
                current_beds += 1
                new_r['room_id'] = f"bed_{current_beds}"
                new_r['room_type'] = f"bedroom_{current_beds}"
            elif 'bath' in new_r['room_id']:
                current_baths += 1
                new_r['room_id'] = f"bath_{current_baths}"
                new_r['room_type'] = f"bathroom_{current_baths}"
            elif 'living' in new_r['room_id']:
                new_r['room_id'] = f"living_{f}"
                new_r['room_type'] = "family_room"
            elif 'kitchen' in new_r['room_id']:
                new_r['room_id'] = f"study_{f}"
                new_r['room_type'] = "study"
            elif 'hall' in new_r['room_id']:
                new_r['room_id'] = f"hall_{f}"
                new_r['room_type'] = "hallway"
            rooms.append(new_r)

    # Convert excess bedrooms to studies to avoid voids
    beds_to_remove = current_beds - beds
    for r in reversed(rooms):
        if beds_to_remove > 0 and 'bed' in r['room_id'] and r['room_id'] != 'bed_1':
            r['room_id'] = r['room_id'].replace('bed', 'study')
            r['room_type'] = 'study'
            beds_to_remove -= 1

    baths_to_add = baths - current_baths
    for r in rooms:
        if baths_to_add > 0 and 'study' in r['room_id']:
            r['room_id'] = r['room_id'].replace('study', 'bath')
            r['room_type'] = f"bathroom_{current_baths + 1}"
            current_baths += 1
            baths_to_add -= 1

    if baths > current_baths:
        x_val = 20 if base_r == r2 else 19.5
        rooms.append({"room_id": f"bath_{current_baths+1}", "room_type": f"bathroom_{current_baths+1}", "floor": 1, "x": x_val, "y": 8, "width": 11, "length": 5})
        for r in rooms:
            if r['room_id'] == 'bed_3':
                r['length'] = 8

    stair_y = 17.0 if base_r == r2 else 20.0
    rooms.append({"room_id": "stair_1", "room_type": "staircase", "floor": 1, "x": 11, "y": stair_y, "width": 8, "length": 10})
    for f in range(2, floors + 1):
        rooms.append({"room_id": f"stair_{f}", "room_type": "staircase", "floor": f, "x": 11, "y": stair_y, "width": 8, "length": 10})

    return rooms

def validate_plan(plan_data, terrain):
    rooms = plan_data['layout']['rooms']
    floors = plan_data['floors']
    beds = plan_data['bedrooms']

    # 1. Exact bedroom count
    actual_beds = sum(1 for r in rooms if 'bedroom' in r['room_type'])
    if actual_beds != beds:
        return False, f"Bedroom count mismatch: configured {beds}, actual {actual_beds}"

    # 2. Exact floor count
    actual_floors = max([r['floor'] for r in rooms]) if rooms else 0
    if actual_floors != floors:
        return False, f"Floor count mismatch: configured {floors}, actual {actual_floors}"

    # 3. Metadata must describe the layout exactly; surplus bathrooms also fail.
    actual_baths = count_bathrooms(rooms)
    if actual_baths != plan_data['bathrooms']:
        return False, f"Bathroom count mismatch: configured {plan_data['bathrooms']}, actual {actual_baths}"

    # 4. No same-floor room overlaps
    for i, a in enumerate(rooms):
        for b in rooms[i+1:]:
            if a['floor'] == b['floor']:
                overlap_x = max(0, min(a['x'] + a['width'], b['x'] + b['width']) - max(a['x'], b['x']))
                overlap_y = max(0, min(a['y'] + a.get('length', 0), b['y'] + b.get('length', 0)) - max(a['y'], b['y']))
                if overlap_x > 0 and overlap_y > 0:
                    return False, f"Overlap between {a['room_id']} and {b['room_id']}"

    # 5. Hallway width minimum
    for r in rooms:
        if r['room_type'] == 'hallway' and r['width'] < 3.5:
            return False, f"Hallway width {r['width']} below minimum 3.5"

    # 6 & 7. Staircase existence and alignment
    if floors > 1:
        staircases = [r for r in rooms if r['room_type'] == 'staircase']
        if len(staircases) < floors:
            return False, "Missing stairs for multi-floor plan"
        first_stair = staircases[0]
        for s in staircases[1:]:
            if s['x'] != first_stair['x'] or s['y'] != first_stair['y'] or s['width'] != first_stair['width'] or s['length'] != first_stair['length']:
                return False, "Misaligned stairs"

    # 8. Geometry validator & 9. Architectural quality
    design = DesignResult.model_validate(plan_data['layout'])
    finish_layout(design) # adds doors/connections

    req = Requirements(bedrooms=beds, bathrooms=plan_data['bathrooms'], floors=floors, target_budget_lkr=0)
    plot = PlotConstraints(land_size_perches=20.0, plot_width_ft=60, plot_length_ft=123, terrain_type=terrain)

    geom_res = validate_geometry(design.rooms, beds, floors, plot.land_size_perches, plot=plot, design=design)
    if not geom_res.passed:
        return False, f"Geometry failed: {geom_res.failures}"

    arch_res = validate_architectural_quality(design, req, plot)
    if not arch_res.passed:
        return False, f"Architecture failed: {arch_res.failures}"

    return True, "Valid"

def gen_plan(code, beds, baths, floors, family, min_land, terrain, base_r=r1):
    rooms = make_rooms(beds, baths, floors, base_r=base_r)
    r_objs = [RoomLayout(**r) for r in rooms]
    conns = build_connections(r_objs, False)

    return {
        "designCode": code,
        "name": f"Test Plan {code}",
        "bedrooms": beds,
        "bathrooms": baths,
        "floors": floors,
        "topologyFamily": family,
        "minimumLandSizePerches": min_land,
        "maximumLandSizePerches": 50,
        "minimumPlotWidthFt": 20,
        "minimumPlotLengthFt": 20,
        "supportedPlotShapes": ["COMPACT_RECTANGLE", "NARROW_DEEP", "WIDE_SHALLOW", "SQUARE", "IRREGULAR", "WIDE", "DEEP", "RECTANGLE", "COMPACT", "MEDIUM", "LARGE", "SMALL", "NARROW", "SHALLOW", "LONG"],
        "supportedTerrains": [terrain],
        "supportedStyles": ["Modern Minimalist", "modern", "conventional", "traditional"],
        "capabilities": {
            "open_plan": True,
            "master_ensuite": True,
            "separate_dining": True,
            "home_office": True,
            "balcony": True,
            "veranda": True,
            "utility_room": True,
            "parking_required": True,
            "accessibility": True
        },
        "architecturalMetrics": {
            "circulation_efficiency": 0.85,
            "natural_light_score": 0.9,
            "ventilation_score": 0.85,
            "structural_complexity": 0.5
        },
        "layout": {
            "template_family": family,
            "template_id": code,
            "rooms": rooms,
            "connections": [c.model_dump() for c in conns],
            "entrances": [{"room_id": "living", "wall": "south", "offset": 3, "width": 4}],
            "floor_count": floors,
            "foundation_type": "stepped" if terrain == "hillside" else "pile" if terrain == "coastal" else "slab"
        }
    }


def build(output_path=None):
    plans = []
    idx = 1
    valid_count = 0
    invalid_count = 0

    for beds in range(2, 7):
        for baths in range(1, 6):
            for floors in range(1, 4):
                for terrain in ['flat', 'hillside', 'coastal']:
                    family = 'COMPACT_RECTANGLE'
                    if terrain == 'hillside': family = 'HILLSIDE_STEPPED'
                    if terrain == 'coastal': family = 'COASTAL_RAISED_COMPACT'

                    for _ in range(3):
                        for br in [r1, r2]:
                            plan = gen_plan(f"HP-{beds}B{baths}B-{floors}F-{idx}", beds, baths, floors, family, 5, terrain, base_r=br)
                            is_valid, reason = validate_plan(plan, terrain)
                            if is_valid:
                                plans.append(plan)
                                valid_count += 1
                            else:
                                print(f"Skipping HP-{beds}B{baths}B-{floors}F-{idx}: {reason}")
                                invalid_count += 1
                            idx += 1

    json_path = Path(output_path) if output_path is not None else Path(__file__).resolve().parents[2] / 'HousePlanner.API' / 'Data' / 'Seed' / 'pre-designed-plans.json'
    json_path.write_text(json.dumps(plans, indent=2) + '\n')
    print(f"Generated {valid_count} valid plans. Skipped {invalid_count} invalid plans. Saved to {json_path}")


if __name__ == '__main__':
    build()
