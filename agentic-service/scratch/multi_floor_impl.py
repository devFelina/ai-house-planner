import time
from typing import Any
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.spatial_program import SpatialProgram
from app.schemas.design_result import DesignResult, RoomLayout
from app.design.exceptions import GenerationFailure
from app.validation.geometry_validator import validate_geometry
from app.design.program.room_rules import rule_for

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

class LayoutSolver:
    def __init__(self, program, plot):
        self.program = program
        self.plot = plot
        self.env_w = plot.buildable_width
        self.env_l = plot.buildable_length
        self.global_evals = 0
        self.global_backtracks = 0
        self.MAX_BACKTRACKS = 500
        self.stair_candidates_evaluated = 0

    def generate(self):
        # 1. basic floor checks
        if self.program.floor_count > 2:
            raise GenerationFailure("ONLY_UP_TO_2_FLOORS_SUPPORTED_IN_G2B")
            
        floors_present = {r.floor for r in self.program.rooms}
        if floors_present != set(range(1, self.program.floor_count + 1)):
            raise GenerationFailure("NON_CONTIGUOUS_OR_MISSING_FLOORS")

        # 2. pre-process rooms
        self.rooms_by_floor = {f: [] for f in range(1, self.program.floor_count + 1)}
        for r in self.program.rooms:
            norm_type = _normalize_room_type(r.type)
            rule = rule_for(norm_type)
            safe_target = max(r.target_area_sqft, rule.min_width * rule.min_length)
            
            if rule.min_width > self.env_w or rule.min_length > self.env_l:
                raise GenerationFailure("ROOM_MIN_DIMENSIONS_EXCEED_PLOT")
                
            self.rooms_by_floor[r.floor].append({
                'intent': r,
                'norm_type': norm_type,
                'target': safe_target,
                'rule': rule
            })
            
        for f in self.rooms_by_floor:
            self.rooms_by_floor[f].sort(key=lambda x: x['target'], reverse=True)

        if self.program.floor_count == 1:
            placed = self._solve_floor(1, self.rooms_by_floor[1], [], self.env_w, self.env_l, 0, 0)
            if placed is None:
                if self.global_backtracks > self.MAX_BACKTRACKS:
                    raise GenerationFailure("VERTICAL_SEARCH_LIMIT_EXCEEDED")
                raise GenerationFailure("NO_NON_OVERLAPPING_PLACEMENT")
            return self._build_result(placed)
            
        # Multi-floor logic
        stair_rule = rule_for('staircase')
        stair_w, stair_l = stair_rule.min_width, stair_rule.min_length
        if self.env_w < stair_w or self.env_l < stair_l:
            raise GenerationFailure("STAIR_CORE_UNPLACEABLE")
            
        core_intent = self.program.vertical_core
        stair_pos = core_intent.stair_position if core_intent else 'CENTER'
        align_service = core_intent.align_service_zones if core_intent else False
        
        # 3 locations for stair
        y_base, x_base = self.env_l / 2 - stair_l / 2, self.env_w / 2 - stair_w / 2
        if 'FRONT' in stair_pos: y_base = 0.0 if self.plot.road_side.lower() == 'south' else self.env_l - stair_l
        elif 'REAR' in stair_pos: y_base = self.env_l - stair_l if self.plot.road_side.lower() == 'south' else 0.0
            
        if 'LEFT' in stair_pos: x_base = 0.0 if self.plot.road_side.lower() in ['south', 'north'] else self.env_l / 2
        elif 'RIGHT' in stair_pos: x_base = self.env_w - stair_w if self.plot.road_side.lower() in ['south', 'north'] else self.env_w
            
        core_cands = [(x_base, y_base, stair_w, stair_l)]
        center = (self.env_w / 2 - stair_w / 2, self.env_l / 2 - stair_l / 2, stair_w, stair_l)
        if center not in core_cands:
            core_cands.append(center)
            
        best_full_layout = None
        best_score = float('inf')
        
        for cx, cy, cw, cl in core_cands:
            self.stair_candidates_evaluated += 1
            s1 = PlacedRoom('staircase_1', 'staircase', 1, cx, cy, cw, cl, cw*cl)
            f1_placed = self._solve_floor(1, self.rooms_by_floor[1], [s1], self.env_w, self.env_l, 0, 0)
            if not f1_placed:
                continue
                
            min_x = min(r.x for r in f1_placed)
            min_y = min(r.y for r in f1_placed)
            max_x = max(r.x + r.width for r in f1_placed)
            max_y = max(r.y + r.length for r in f1_placed)
            
            s2 = PlacedRoom('staircase_2', 'staircase', 2, cx, cy, cw, cl, cw*cl)
            f2_placed = self._solve_floor(2, self.rooms_by_floor[2], [s2], max_x - min_x, max_y - min_y, min_x, min_y, support_rooms=f1_placed)
            
            if f2_placed:
                score = self._score_full_layout(f1_placed, f2_placed, align_service)
                if score < best_score:
                    best_score = score
                    best_full_layout = f1_placed + f2_placed
                    
        if best_full_layout is None:
            if self.global_backtracks > self.MAX_BACKTRACKS:
                raise GenerationFailure("VERTICAL_SEARCH_LIMIT_EXCEEDED")
            raise GenerationFailure("GROUND_FLOOR_UNSOLVABLE" if self.stair_candidates_evaluated > 0 else "STAIR_CORE_UNPLACEABLE")
            
        return self._build_result(best_full_layout)

    def _solve_floor(self, floor_idx: int, rooms: list, current_placed: list, bound_w: float, bound_l: float, offset_x: float, offset_y: float, support_rooms=None) -> list[PlacedRoom] | None:
        def backtrack(room_idx: int, placed: list[PlacedRoom]) -> list[PlacedRoom] | None:
            if room_idx == len(rooms):
                return placed
                
            rp = rooms[room_idx]
            intent = rp['intent']
            rule = rp['rule']
            target_a = rp['target']
            
            candidates = []
            w = rule.min_width
            while w <= bound_w and w * rule.min_length <= target_a * 1.2:
                l = target_a / w
                if rule.min_length <= l <= bound_l:
                    if (w / l <= rule.aspect_limit) and (l / w <= rule.aspect_limit):
                        candidates.append((w, l))
                w += 1.0
                
            if not candidates:
                sq = target_a ** 0.5
                candidates.append((sq, sq))
                
            placements = []
            for cand_w, cand_l in candidates:
                x = offset_x
                while x + cand_w <= offset_x + bound_w + 0.01:
                    y = offset_y
                    while y + cand_l <= offset_y + bound_l + 0.01:
                        self.global_evals += 1
                        
                        overlap = False
                        shared_wall = False if placed else True
                        
                        for p in placed:
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
                            
                        if support_rooms:
                            corners = [(x,y), (x+cand_w,y), (x,y+cand_l), (x+cand_w,y+cand_l)]
                            supported = True
                            for cx, cy in corners:
                                c_supp = False
                                for sr in support_rooms:
                                    if cx >= sr.x - 0.01 and cx <= sr.x + sr.width + 0.01 and cy >= sr.y - 0.01 and cy <= sr.y + sr.length + 0.01:
                                        c_supp = True
                                        break
                                if not c_supp:
                                    supported = False
                                    break
                            if not supported:
                                y += 1.0
                                continue

                        exterior = (x < 0.1 or y < 0.1 or x + cand_w > self.env_w - 0.1 or y + cand_l > self.env_l - 0.1)
                        if intent.exterior_wall_required and not exterior:
                            y += 1.0
                            continue
                            
                        score = 0.0
                        cx = x + cand_w / 2
                        cy = y + cand_l / 2
                        road = self.plot.road_side.lower()
                        ideal_x, ideal_y = self.env_w / 2, self.env_l / 2 
                        
                        if 'FRONT' in intent.preferred_position:
                            if road == 'south': ideal_y = 0
                            elif road == 'north': ideal_y = self.env_l
                            elif road == 'west': ideal_x = 0
                            elif road == 'east': ideal_x = self.env_w
                        elif 'REAR' in intent.preferred_position:
                            if road == 'south': ideal_y = self.env_l
                            elif road == 'north': ideal_y = 0
                            elif road == 'west': ideal_x = self.env_w
                            elif road == 'east': ideal_x = 0
                            
                        if 'LEFT' in intent.preferred_position:
                            ideal_x = 0 if road in ('south', 'north') else ideal_y
                        elif 'RIGHT' in intent.preferred_position:
                            ideal_x = self.env_w if road in ('south', 'north') else ideal_y
                            
                        dist_to_ideal = ((cx - ideal_x)**2 + (cy - ideal_y)**2)**0.5
                        score += dist_to_ideal * 10
                        
                        for adj in self.program.adjacencies:
                            other = next((p for p in placed if p.id == adj.room_a or p.id == adj.room_b), None)
                            if other and (adj.room_a == intent.id or adj.room_b == intent.id):
                                ocx, ocy = other.x + other.width / 2, other.y + other.length / 2
                                dist = ((cx - ocx)**2 + (cy - ocy)**2)**0.5
                                weight = 50 if adj.priority == 'HIGH' else 20
                                if adj.relationship == 'ADJACENT':
                                    score += dist * weight * 2
                                elif adj.relationship == 'NEAR':
                                    score += dist * weight
                                elif adj.relationship == 'SEPARATE':
                                    score -= dist * weight 
                                    
                        placements.append((score, x, y, cand_w, cand_l))
                        y += 1.0
                    x += 1.0
                    
            placements.sort(key=lambda item: item[0])
            top_k = 10
            
            for score, x, y, w, l in placements[:top_k]:
                new_placed = list(placed)
                new_placed.append(PlacedRoom(intent.id, rp['norm_type'], intent.floor, x, y, w, l, target_a))
                
                res = backtrack(room_idx + 1, new_placed)
                if res is not None:
                    return res
                    
                self.global_backtracks += 1
                if self.global_backtracks > self.MAX_BACKTRACKS:
                    return None
                    
            return None
            
        return backtrack(0, current_placed)
        
    def _score_full_layout(self, f1, f2, align_service):
        score = 0
        if align_service:
            f2_service = [r for r in f2 if r.type in ['bathroom', 'utility']]
            f1_service = [r for r in f1 if r.type in ['bathroom', 'utility', 'kitchen']]
            for u in f2_service:
                ucx = u.x + u.width/2
                ucy = u.y + u.length/2
                min_dist = min((((l.x+l.width/2 - ucx)**2 + (l.y+l.length/2 - ucy)**2)**0.5 for l in f1_service), default=0)
                score += min_dist * 20
        return score
        
    def _build_result(self, placed: list[PlacedRoom]):
        result = DesignResult(
            floor_count=self.program.floor_count,
            foundation_type="slab",
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
        ground_area = sum(r.width * r.length for r in result.rooms if r.floor == 1)
        result.ground_footprint_sqft = ground_area
        
        val_result = validate_geometry(
            result.rooms,
            expected_bedrooms=sum(1 for r in self.program.rooms if "bedroom" in r.type.lower()),
            expected_floors=self.program.floor_count,
            land_size_perches=self.plot.land_size_perches,
            plot=self.plot,
            design=None
        )
        if not val_result.passed:
            raise GenerationFailure(f"GEOMETRY_VALIDATION_FAILED: {val_result.failures[0]}")
            
        meta = {
            "floor_count": self.program.floor_count,
            "rooms_requested": len(self.program.rooms),
            "rooms_placed": len(placed),
            "candidate_evaluations": self.global_evals,
            "floor_candidate_evaluations": self.global_evals,
            "core_candidates_evaluated": self.stair_candidates_evaluated,
            "backtracks": self.global_backtracks,
            "program_target_area": sum(r.target_area_sqft for r in self.program.rooms),
            "actual_room_area": actual_area,
            "ground_footprint_area": ground_area,
            "upper_footprint_area": actual_area - ground_area if self.program.floor_count > 1 else 0,
            "buildable_area": self.env_w * self.env_l,
            "generation_ms": 0,
            "placement_score": 100,
            "failure_reason": None
        }
        return result, meta

def generate_geometry(program: SpatialProgram, plot: PlotConstraints) -> tuple[DesignResult, dict[str, Any]]:
    start_ms = time.time() * 1000
    solver = LayoutSolver(program, plot)
    res, meta = solver.generate()
    meta["generation_ms"] = int((time.time() * 1000) - start_ms)
    return res, meta
