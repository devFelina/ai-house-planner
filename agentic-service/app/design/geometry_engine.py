"""Parametric room banks used only by the disclosed offline demo fallback."""
from math import sqrt
from app.design.adjacency import build_connections, exterior_segments, road_access_clear
from app.design.diversity import candidate_rng, stable_id, stable_seed
from app.design.models import Entrance, Requirements, SpatialProgram, RoomSpec
from app.design.plot_constraints import PlotConstraints
from app.design.room_rules import room_kind
from app.schemas.design_result import DesignResult, RoomLayout, Opening

TERRAIN_FOUNDATION_MAP = {'flat': 'slab', 'hillside': 'stepped', 'coastal': 'raised'}


def generate_geometry(program: SpatialProgram, req: Requirements, plot: PlotConstraints,
                      family: str, seed: int, candidate_index: int) -> DesignResult:
    rng = candidate_rng(seed, family, candidate_index)
    # Controlled size variants; smaller variants remain above room-specific minima.
    size_factor = (1.0, 0.82, 0.55)[candidate_index % 3]
    circulation_width = 5.0 if req.accessibility else 4.0
    if family == 'CENTRAL_CORE':
        circulation_width = 8.0
    rooms: list[RoomLayout] = []
    prefix = f'{seed}:{family}:{candidate_index}:{stable_seed({"requirements": req.model_dump(), "plot": plot.model_dump()})}'

    def put(key: str, kind: str, floor: int, x: float, y: float, w: float, d: float) -> None:
        rooms.append(RoomLayout(room_id=stable_id(prefix+':'+key), room_type=kind,
                                floor=floor, x=round(x, 4), y=round(y, 4),
                                width=round(w, 4), length=round(d, 4)))

    def dimensions(spec: RoomSpec) -> tuple[float, float]:
        target = max(spec.min_width*spec.min_length, spec.target_area*size_factor)
        w = round(max(spec.min_width, sqrt(target) * rng.uniform(0.95, 1.05)), 1)
        d = round(max(spec.min_length, target/w), 1)
        return min(spec.max_width, w), min(spec.max_length, d)

    for floor in range(1, req.floors+1):
        specs = [s for s in program.rooms if s.floor == floor]
        # Keep public adjacencies and the optional master/ensuite pair contiguous.
        priority = {'living_room': 0, 'dining': 1, 'kitchen': 2, 'bedroom_1': 4, 'bathroom_attached': 4.1}
        specs.sort(key=lambda s: (priority.get(s.id, 5 if s.zone == 'private' else 6), s.id))
        sized = [(s, *dimensions(s)) for s in specs]
        cw = circulation_width
        def bank(items: list, x: float, y: float, side: str) -> float:
            pos = 0.0
            for spec, w, d in items:
                if side == 'north':
                    put(spec.id, spec.room_type, floor, x+pos, y, w, d)
                elif side == 'south':
                    put(spec.id, spec.room_type, floor, x+pos, y-d, w, d)
                elif side == 'east':
                    put(spec.id, spec.room_type, floor, x, y-pos-w, d, w)
                pos = round(pos+w, 4)
            return pos
        if family == 'LINEAR':
            span = bank(sized, cw, 0, 'east')
            put(f'hall_{floor}', 'hallway', floor, 0, -span, cw, span)
            if req.floors > 1:
                put(f'stair_{floor}', 'staircase', floor, cw, 0, 6, 10)
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
        else:
            if family == 'SPLIT_ZONE':
                top = [x for x in sized if x[0].zone in ('public', 'service') and not x[0].id.startswith('bathroom')]
                bottom = [x for x in sized if x not in top]
            else:
                split = (len(sized)+1)//2
                # Required pairs may not straddle banks.
                while split < len(sized) and (sized[split][0].id in ('kitchen', 'bathroom_attached')):
                    split += 1
                top, bottom = sized[:split], sized[split:]
            offset = 4.0 if family == 'HILLSIDE_STEPPED' else 0.0
            a = bank(top, 0, cw, 'north')
            b = bank(bottom, offset, 0, 'south') + offset
            span = max(a, b, 6)
            put(f'hall_{floor}', 'foyer' if family == 'CENTRAL_CORE' else 'hallway', floor, 0, 0, span, cw)
            if req.floors > 1:
                put(f'stair_{floor}', 'staircase', floor, -6, 0, 6, 10)

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
            entries = [(r, wall, lo, hi) for r in rotated if r.floor == 1 and room_kind(r.room_type) in ('hallway', 'foyer')
                       for wall, lo, hi in exterior_segments(r, rotated) if wall == plot.effective_entrance_side and road_access_clear(r, rotated, wall, (lo+hi-3)/2)]
            if entries:
                # Select the circulation opening closest to the road edge.
                def road_distance(entry: tuple) -> float:
                    r = entry[0]
                    return {'south': r.y, 'north': length-r.y-r.length,
                            'west': r.x, 'east': width-r.x-r.width}[plot.effective_entrance_side]
                entry = min(entries, key=road_distance)
                slope_penalty = width if plot.terrain_type == 'hillside' and plot.slope_direction in ('north', 'south') else 0
                options.append((road_distance(entry)+slope_penalty, turns, rotated, entry))
    if not options:
        raise ValueError('Generated footprint/road-facing entrance does not fit the buildable plot.')
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
