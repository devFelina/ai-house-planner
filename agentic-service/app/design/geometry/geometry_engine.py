"""Parametric room banks used as the primary deterministic layout generator."""
from math import sqrt

from app.design.geometry.adjacency import build_connections, exterior_segments, road_access_clear
from app.design.generation.diversity import candidate_rng, stable_id, stable_seed
from app.design.program.models import Entrance, Requirements, RoomSpec, SpatialProgram
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.room_rules import room_kind
from app.schemas.design_result import DesignResult, Opening, RoomLayout

TERRAIN_FOUNDATION_MAP = {'flat': 'slab', 'hillside': 'stepped', 'coastal': 'raised'}

def generate_geometry(program: SpatialProgram, req: Requirements, plot: PlotConstraints,
                      family: str, seed: int, candidate_index: int) -> DesignResult:
    rng = candidate_rng(seed, family, candidate_index)
    # Calculate base minimum program area
    min_program_area = sum(spec.min_width * spec.min_length for spec in program.rooms)

    # Calculate available footprint vs required footprint
    available_ratio = plot.maximum_ground_footprint / max(min_program_area, 1)

    # Scale from 0.82 (very tight) to 1.5 (very generous) based on available land
    base_factor = min(1.5, max(0.82, available_ratio * 0.7))

    # Apply a wide variance per candidate index so that at least one candidate
    # shrinks aggressively enough to fit tight boundaries, even when base_factor is high.
    size_factor = base_factor * (1.0, 0.75, 0.5)[candidate_index % 3]
    circulation_width = 5.0 if req.accessibility else 4.0
    if family == 'CENTRAL_CORE':
        circulation_width = 8.0
    rooms: list[RoomLayout] = []
    prefix = f'{seed}:{family}:{candidate_index}:{stable_seed({"requirements": req.model_dump(), "plot": plot.model_dump()})}'

    def put(key: str, kind: str, floor: int, x: float, y: float, w: float, d: float) -> None:
        rooms.append(RoomLayout(room_id=stable_id(prefix+':'+key), room_type=kind,
                                floor=floor, x=round(x, 4), y=round(y, 4),
                                width=round(w, 4), length=round(d, 4)))

    # On extremely tight plots, allow minimums to compress slightly (up to 25%)
    # to prevent mathematically impossible layouts, but only for the smallest candidate.
    min_scale = min(1.0, max(0.75, available_ratio * 0.9)) if candidate_index == 2 else 1.0

    def dimensions(spec: RoomSpec) -> tuple[float, float]:
        target = max(spec.min_width * spec.min_length * (min_scale ** 2), spec.target_area * size_factor)
        # Adapt room aspect ratio to the plot's buildable aspect ratio
        buildable_aspect = plot.buildable_width / plot.buildable_length if plot.buildable_length > 0 else 1.0
        # Limit stretch to reasonable room proportions (0.5 to 2.0)
        aspect_stretch = max(0.5, min(2.0, buildable_aspect))

        w = round(max(spec.min_width * min_scale, sqrt(target) * aspect_stretch * rng.uniform(0.95, 1.05)), 1)
        d = round(target/w, 1)
        # Cap depth for LINEAR to ensure it fits the narrow plot
        if family == 'LINEAR' and d > (plot.buildable_width - circulation_width):
            d = max(spec.min_length * min_scale, plot.buildable_width - circulation_width)
            w = round(target/d, 1)
        # also apply min_scale to depth enforcement
        if d < spec.min_length * min_scale:
            d = round(spec.min_length * min_scale, 1)
            w = round(target/d, 1)
        return min(spec.max_width, w), min(spec.max_length, d)

    stair_core = None

    floor_specs = {}
    for floor in range(1, req.floors+1):
        specs = [s for s in program.rooms if s.floor == floor]
        priority = {'living_room': 0, 'dining': 1, 'kitchen': 2, 'bedroom_1': 4, 'bathroom_attached': 4.1}
        specs.sort(key=lambda s: (priority.get(s.id, 5 if s.zone == 'private' else 6), s.id))
        floor_specs[floor] = [(s, *dimensions(s)) for s in specs]

    # Equalize lengths across floors so they align structurally.
    if req.floors > 1:
        if family == 'LINEAR' and floor_specs.get(1) and floor_specs.get(2):
            span1 = sum(d for _, w, d in floor_specs[1])
            span2 = sum(d for _, w, d in floor_specs[2])
            max_span = max(span1, span2)
            if span1 < max_span:
                s, w, d = floor_specs[1][-1]
                floor_specs[1][-1] = (s, w, d + (max_span - span1))
        elif family in ('COMPACT_RECTANGLE', 'CENTRAL_CORE', 'SPLIT_ZONE', 'HILLSIDE_STEPPED') and floor_specs.get(1) and floor_specs.get(2):
            def calc_top_span(f_specs):
                if family == 'SPLIT_ZONE':
                    top = [x for x in f_specs if x[0].zone in ('public', 'service') and not x[0].id.startswith('bathroom')]
                else:
                    split = (len(f_specs)+1)//2
                    top_w, bot_w = sum(x[1] for x in f_specs[:split]), sum(x[1] for x in f_specs[split:])
                    while split > 1 and top_w > bot_w * 1.5:
                        split -= 1; top_w, bot_w = sum(x[1] for x in f_specs[:split]), sum(x[1] for x in f_specs[split:])
                    while split < len(f_specs)-1 and bot_w > top_w * 1.5:
                        split += 1; top_w, bot_w = sum(x[1] for x in f_specs[:split]), sum(x[1] for x in f_specs[split:])
                    top = f_specs[:split]
                return sum(w for _, w, d in top), top

            top_span1, top1 = calc_top_span(floor_specs[1])
            top_span2, _top2 = calc_top_span(floor_specs[2])
            if top_span1 < top_span2 and top1:
                # Add padding to the last room in top1
                s, w, d = top1[-1]
                idx = floor_specs[1].index((s, w, d))
                floor_specs[1][idx] = (s, w + (top_span2 - top_span1), d)

    for floor in range(1, req.floors+1):
        sized = floor_specs[floor]
        cw = circulation_width
        def bank(items: list, x: float, y: float, side: str, floor_number: int = floor) -> float:
            pos = 0.0
            for spec, w, d in items:
                if side == 'north':
                    put(spec.id, spec.room_type, floor_number, x+pos, y, w, d)
                elif side == 'south':
                    put(spec.id, spec.room_type, floor_number, x+pos, y-d, w, d)
                elif side == 'east':
                    put(spec.id, spec.room_type, floor_number, x, y-pos-w, d, w)
                pos = round(pos+w, 4)
            return pos

        if family == 'LINEAR':
            span = bank(sized, cw, 0, 'east')
            put(f'hall_{floor}', 'hallway', floor, 0, -span, cw, span)
            if req.floors > 1:
                if floor == 1:
                    stair_core = (cw, 0, 6, 10)
                if stair_core:
                    put(f'stair_{floor}', 'staircase', floor, *stair_core)
                if floor == 1:
                    put(f'foyer_{floor}', 'foyer', floor, 0, 0, cw, 10)
        elif family in ('L_SHAPE', 'T_SHAPE'):
            public_count = sum(s.zone == 'public' or s.id == 'kitchen' for s in specs)
            split = max(2, public_count)
            first, rest = sized[:split], sized[split:]

            span = bank(first, 0, cw, 'north')
            if family == 'L_SHAPE':
                depth = bank(rest, span+cw, 0, 'east')
                put(f'hall_{floor}', 'hallway', floor, 0, 0, span+cw, cw)
                if depth:
                    put(f'branch_{floor}', 'hallway', floor, span, -depth, cw, depth)
            else:
                # Private rooms flank a stem below the public crossbar.
                mid = max(10, span/2)
                left, right = rest[::2], rest[1::2]
                depths = []
                for items, side in [(left, 'left'), (right, 'right')]:
                    pos = 0.0
                    for spec, w, d in items:
                        put(spec.id, spec.room_type, floor, mid-w if side == 'left' else mid+cw,
                            -pos-d, w, d)
                        pos = round(pos+d, 4)
                    depths.append(pos)
                put(f'hall_{floor}', 'hallway', floor, 0, 0, max(span, mid+cw), cw)
                if max(depths):
                    put(f'branch_{floor}', 'hallway', floor, mid, -max(depths), cw, max(depths))
            if req.floors > 1:
                if floor == 1:
                    stair_core = (0, 0, 6, 10)
                if stair_core:
                    put(f'stair_{floor}', 'staircase', floor, *stair_core)
        else:
            if family == 'SPLIT_ZONE':
                top = [x for x in sized if x[0].zone in ('public', 'service') and not x[0].id.startswith('bathroom')]
                bottom = [x for x in sized if x not in top]
            else:
                split = (len(sized)+1)//2
                # Balance the split dynamically based on accumulated widths to avoid one massive bank
                top_w = sum(x[1] for x in sized[:split])
                bot_w = sum(x[1] for x in sized[split:])
                # Shift split if heavily unbalanced
                while split > 1 and top_w > bot_w * 1.5:
                    split -= 1
                    top_w = sum(x[1] for x in sized[:split])
                    bot_w = sum(x[1] for x in sized[split:])
                while split < len(sized)-1 and bot_w > top_w * 1.5:
                    split += 1
                    top_w = sum(x[1] for x in sized[:split])
                    bot_w = sum(x[1] for x in sized[split:])

                top, bottom = sized[:split], sized[split:]

            offset = 4.0 if family == 'HILLSIDE_STEPPED' else 0.0
            a = bank(top, 0, cw, 'north')
            b = bank(bottom, offset, 0, 'south') + offset

            span = max(a, b, 6)
            put(f'hall_{floor}', 'foyer' if family == 'CENTRAL_CORE' else 'hallway', floor, 0, 0, span, cw)
            if req.floors > 1:
                if floor == 1:
                    stair_core = (-6, 0, 6, 10)
                if stair_core:
                    put(f'stair_{floor}', 'staircase', floor, *stair_core)

    # Long narrow-plot circulation is represented by connected segments so each
    # space stays within the centralized 50 ft dimension limit.
    for hall in list(rooms):
        if room_kind(hall.room_type) not in ('hallway', 'foyer') or max(hall.width, hall.length) <= 50:
            continue
        rooms.remove(hall)
        count = int(max(hall.width, hall.length)/40)+1
        for index in range(count):
            horizontal = hall.width >= hall.length
            w = hall.width/count if horizontal else hall.width
            d = hall.length if horizontal else hall.length/count
            rooms.append(RoomLayout(room_id=stable_id(hall.room_id+str(index)), room_type=hall.room_type,
                                    floor=hall.floor, x=hall.x+index*w if horizontal else hall.x,
                                    y=hall.y if horizontal else hall.y+index*d, width=w, length=d))

    # Rotate the entire building, including all stair cores, as one unit.
    # Prefer an entrance facing the road, then the orientation that fits the plot.
    options = []
    for turns in range(4):
        rotated = [r.model_copy(deep=True) for r in rooms]
        for r in rotated:
            for _ in range(turns):
                r.x, r.y, r.width, r.length = -r.y-r.length, r.x, r.length, r.width
        min_x, min_y = min(r.x for r in rotated), min(r.y for r in rotated)
        for r in rotated:
            r.x, r.y = round(r.x-min_x, 4), round(r.y-min_y, 4)
        width = max(r.x+r.width for r in rotated)
        length = max(r.y+r.length for r in rotated)
        if width <= plot.buildable_width+0.001 and length <= plot.buildable_length+0.001:
            entries = [(r, wall, lo, hi) for r in rotated if r.floor == 1 and room_kind(r.room_type) in ('hallway', 'foyer', 'living_room')
                       for wall, lo, hi in exterior_segments(r, rotated) if wall == plot.effective_entrance_side and road_access_clear(r, rotated, wall, (lo+hi-3)/2)]
            if entries:
                # Select the circulation opening closest to the road edge.
                def road_distance(entry: tuple, building_width: float = width, building_length: float = length) -> float:
                    r = entry[0]
                    return {'south': r.y, 'north': building_length-r.y-r.length,
                            'west': r.x, 'east': building_width-r.x-r.width}[plot.effective_entrance_side]
                entry = min(entries, key=road_distance)
                slope_penalty = width if plot.terrain_type == 'hillside' and plot.slope_direction in ('north', 'south') else 0
                options.append((road_distance(entry)+slope_penalty, turns, rotated, entry))
    if not options:
        # Debug why it didn't fit
        w0 = max(r.x + r.width for r in rooms) if rooms else 0
        l0 = max(r.y + r.length for r in rooms) if rooms else 0
        raise ValueError(f'Generated footprint/road-facing entrance does not fit the buildable plot. Generated: {w0}x{l0}, Buildable: {plot.buildable_width}x{plot.buildable_length}. Topology: {family}, Area: {plot.maximum_ground_footprint}')
    _, _, rooms, (entrance_room, wall, lo, hi) = min(options, key=lambda o: (o[0], o[1]))
    connections = build_connections(rooms, req.open_plan)
    entrance = Entrance(room_id=entrance_room.room_id, wall=wall, offset=round((lo+hi-3)/2, 4))
    entrance_room.doors.append(Opening(wall=wall, offset=entrance.offset, width=entrance.width))
    for r in rooms:
        if room_kind(r.room_type) in ('bedroom', 'living_room', 'home_office', 'dining', 'family_lounge'):
            segments = exterior_segments(r, rooms)
            if segments:
                side, start, end = max(segments, key=lambda s: s[2]-s[1])
                r.windows.append(Opening(wall=side, offset=round((start+end-3)/2, 4), width=3))
    total = round(sum(r.width*r.length for r in rooms), 2)
    return DesignResult(design_id=stable_id(prefix), floor_count=req.floors,
                        total_built_up_area_sqft=total, foundation_type=TERRAIN_FOUNDATION_MAP[plot.terrain_type],
                        terrain_type=plot.terrain_type, template_id=family, template_family=family,
                        design_seed=seed, rooms=rooms, connections=connections, entrances=[entrance],
                        ground_footprint_sqft=round(sum(r.width*r.length for r in rooms if r.floor == 1), 2),
                        plot_constraints=plot.model_dump(), program=program.model_dump())
