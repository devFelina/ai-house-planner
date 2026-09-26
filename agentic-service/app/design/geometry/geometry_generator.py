import time
from typing import Any

from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram
from app.schemas.design_result import DesignResult, RoomLayout
from app.design.exceptions import GenerationFailure
from app.validation.geometry_validator import validate_geometry
from app.design.program.room_rules import rule_for, room_kind

def _normalize_room_type(gpt_type: str) -> str:
    t = gpt_type.lower().replace(' ', '_')
    if t == 'living': return 'living_room'
    if t == 'dining': return 'dining'
    if t == 'bath': return 'bathroom'
    if t == 'master_bedroom': return 'bedroom_master'
    return t

class PlacedRoom:
    def __init__(self, room_id: str, rtype: str, floor: int, x: float, y: float, w: float, h: float, target_area: float):
        self.id = room_id
        self.type = rtype
        self.floor = floor
        self.x = x
        self.y = y
        self.width = w
        self.length = h
        self.target_area = target_area

def generate_geometry(program: SpatialProgram, plot: PlotConstraints) -> tuple[DesignResult, dict[str, Any]]:
    start_ms = time.time() * 1000
    
    if program.floor_count > 1:
        raise GenerationFailure("UNSUPPORTED_MULTI_FLOOR_IN_G2A")
        
    env_w = plot.buildable_width
    env_l = plot.buildable_length
    
    # 1. Normalize and resolve hard minimums (Step 3)
    # The python room rules own min dimensions and hard minimum area.
    rooms_to_place = []
    for r in program.rooms:
        norm_type = _normalize_room_type(r.type)
        rule = rule_for(norm_type)
        # Python owns the absolute minimum area. We allow GPT's target, but if it violates the hard floor, we bump it up.
        safe_target = max(r.target_area_sqft, rule.min_width * rule.min_length)
        rooms_to_place.append({
            'intent': r,
            'norm_type': norm_type,
            'target': safe_target,
            'rule': rule
        })
        
    # Sort rooms for placement order (Step 15)
    # Strategy: Place largest rooms first (living, master bed) as anchors, then smaller rooms.
    # High priority adjacencies will be evaluated during candidate generation.
    rooms_to_place.sort(key=lambda x: x['target'], reverse=True)
    
    placed: list[PlacedRoom] = []
    
    # A simple BSP-like or Grid-based allocator for the single floor.
    # For G2A, we'll implement a deterministic layout grid that places rooms sequentially
    # finding the first valid non-overlapping bounding box that fits criteria.
    
    MAX_BACKTRACKS = 500
    global_backtracks = [0]
    
    def backtrack_place(room_index: int, current_placed: list[PlacedRoom]) -> list[PlacedRoom] | None:
        if room_index == len(rooms_to_place):
            return current_placed
            
        rp = rooms_to_place[room_index]
        intent = rp['intent']
        rule = rp['rule']
        target_a = rp['target']
        
        candidates = []
        w = rule.min_width
        while w <= env_w and w * rule.min_length <= target_a * 1.2:
            l = target_a / w
            if rule.min_length <= l <= env_l:
                if (w / l <= rule.aspect_limit) and (l / w <= rule.aspect_limit):
                    candidates.append((w, l))
            w += 1.0
            
        if not candidates:
            sq = target_a ** 0.5
            candidates.append((sq, sq))
            
        placements = []
        for cand_w, cand_l in candidates:
            x = 0.0
            while x + cand_w <= env_w + 0.01:
                y = 0.0
                while y + cand_l <= env_l + 0.01:
                    overlap = False
                    shared_wall = False if current_placed else True
                    
                    for p in current_placed:
                        if not (x >= p.x + p.width - 0.01 or x + cand_w <= p.x + 0.01 or 
                                y >= p.y + p.length - 0.01 or y + cand_l <= p.y + 0.01):
                            overlap = True
                            break
                        x_overlap = min(x + cand_w, p.x + p.width) - max(x, p.x)
                        y_overlap = min(y + cand_l, p.y + p.length) - max(y, p.y)
                        
                        if x_overlap >= 2.99 and (abs(y + cand_l - p.y) < 0.01 or abs(p.y + p.length - y) < 0.01):
                            shared_wall = True
                        if y_overlap >= 2.99 and (abs(x + cand_w - p.x) < 0.01 or abs(p.x + p.width - x) < 0.01):
                            shared_wall = True

                    if overlap or not shared_wall:
                        y += 1.0
                        continue
                        
                    exterior = (x < 0.1 or y < 0.1 or x + cand_w > env_w - 0.1 or y + cand_l > env_l - 0.1)
                    if intent.exterior_wall_required and not exterior:
                        y += 1.0
                        continue
                        
                    score = 0.0
                    cx = x + cand_w / 2
                    cy = y + cand_l / 2
                    road = plot.road_side.lower()
                    ideal_x, ideal_y = env_w / 2, env_l / 2 
                    
                    if 'FRONT' in intent.preferred_position:
                        if road == 'south': ideal_y = 0
                        elif road == 'north': ideal_y = env_l
                        elif road == 'west': ideal_x = 0
                        elif road == 'east': ideal_x = env_w
                    elif 'REAR' in intent.preferred_position:
                        if road == 'south': ideal_y = env_l
                        elif road == 'north': ideal_y = 0
                        elif road == 'west': ideal_x = env_w
                        elif road == 'east': ideal_x = 0
                        
                    if 'LEFT' in intent.preferred_position:
                        ideal_x = 0 if road in ('south', 'north') else ideal_y
                    elif 'RIGHT' in intent.preferred_position:
                        ideal_x = env_w if road in ('south', 'north') else ideal_y
                        
                    dist_to_ideal = ((cx - ideal_x)**2 + (cy - ideal_y)**2)**0.5
                    score += dist_to_ideal * 10
                    
                    for adj in program.adjacencies:
                        other = next((p for p in current_placed if p.id == adj.room_a or p.id == adj.room_b), None)
                        if other and (adj.room_a == intent.id or adj.room_b == intent.id):
                            ocx, ocy = other.x + other.width / 2, other.y + other.length / 2
                            dist = ((cx - ocx)**2 + (cy - ocy)**2)**0.5
                            weight = 50 if adj.priority == 'HIGH' else 20
                            if adj.relationship == 'ADJACENT' or adj.relationship == 'NEAR':
                                score += dist * weight
                            elif adj.relationship == 'SEPARATE':
                                score -= dist * weight 
                                
                    placements.append((score, x, y, cand_w, cand_l))
                    y += 1.0
                x += 1.0
                
        # Sort placements by score and take top K to keep branching factor reasonable
        placements.sort(key=lambda item: item[0])
        top_k = 10
        
        for score, x, y, w, l in placements[:top_k]:
            new_placed = list(current_placed)
            new_placed.append(PlacedRoom(intent.id, rp['norm_type'], intent.floor, x, y, w, l, target_a))
            
            res = backtrack_place(room_index + 1, new_placed)
            if res is not None:
                return res
                
            global_backtracks[0] += 1
            if global_backtracks[0] > MAX_BACKTRACKS:
                return None
                
        return None
        
    placed = backtrack_place(0, [])
    if placed is None:
        if global_backtracks[0] > MAX_BACKTRACKS:
            raise GenerationFailure("SEARCH_LIMIT_EXCEEDED")
        raise GenerationFailure("NO_NON_OVERLAPPING_PLACEMENT")
            
    # Build the final DesignResult
    result = DesignResult(
        floor_count=1,
        foundation_type="slab",  # Just default for G2A stub
        terrain_type="flat"
    )
    
    for p in placed:
        result.rooms.append(RoomLayout(
            room_id=p.id,
            room_type=p.type,
            floor=p.floor,
            x=round(p.x, 2),
            y=round(p.y, 2),
            width=round(p.width, 2),
            length=round(p.length, 2)
        ))
        
    actual_area = sum(r.width * r.length for r in result.rooms)
    result.total_built_up_area_sqft = actual_area
    result.ground_footprint_sqft = actual_area
    
    # 5. Run existing Geometry Validator (Step 31)
    val_result = validate_geometry(
        result.rooms,
        expected_bedrooms=sum(1 for r in program.rooms if "bedroom" in r.type.lower()),
        expected_floors=1,
        land_size_perches=plot.land_size_perches,
        plot=plot,
        design=None # G2A does not produce doors/entrances yet
    )
    
    if not val_result.passed:
        # We failed deterministic validation. 
        raise GenerationFailure(f"GEOMETRY_VALIDATION_FAILED: {val_result.failures[0]}")
        
    meta = {
        "rooms_requested": len(rooms_to_place),
        "rooms_placed": len(placed),
        "candidate_evaluations": -1, # disabled
        "backtracks": global_backtracks[0],
        "program_target_area": sum(r['target'] for r in rooms_to_place),
        "actual_room_area": actual_area,
        "buildable_area": env_w * env_l,
        "unused_area": (env_w * env_l) - actual_area,
        "placement_score": 100, # stub
        "generation_ms": int((time.time() * 1000) - start_ms),
        "failure_reason": None
    }
    
    return result, meta
