"""Bounded circulation reservation and privacy checks for semantic generation.

All dimensions use project RoomRules, not legal/code-compliance claims. Rooms
are partitioned around a reserved strip before openings exist. No finished room
is moved. Unsupported programs exhaust the bounded search and fail closed.
"""
from functools import lru_cache
from itertools import combinations
from math import ceil

from app.design.geometry.adjacency import graph_for, reachable
from app.design.program.room_rules import room_kind, rule_for
from app.design.quality.quality_config import QUALITY

PRIVATE = {'bedroom', 'bathroom', 'home_office'}
MAX_FLOOR_PARTITIONS = 128
MAX_BANK_ROOMS = 10
MAX_SLICE_NODES = 2500
MAX_FLOOR_OPTIONS = 20
MAX_RESERVATION_NODES = 180_000


def circulation_failures(design):
    """Reachability with unrelated private nodes removed, plus upper landings."""
    graph = graph_for(design.rooms, design.connections)
    private = {r.room_id for r in design.rooms if room_kind(r.room_type) in PRIVATE}
    starts = [e.room_id for e in design.entrances]
    failures = []
    for room in design.rooms:
        blocked = private - {room.room_id}
        # Preserve the existing, explicit attached-bathroom convention.
        if room.room_type == 'bathroom_attached':
            blocked -= {r.room_id for r in design.rooms if r.room_type == 'bedroom_1'}
        if not any(room.room_id in reachable(graph, start, blocked) for start in starts):
            failures.append({'code': 'PRIVATE_PASS_THROUGH', 'room_id': room.room_id})
    for floor in range(2, design.floor_count + 1):
        stairs = [r for r in design.rooms if r.floor == floor and room_kind(r.room_type) == 'staircase']
        landings = {r.room_id for r in design.rooms if r.floor == floor and
                    room_kind(r.room_type) in {'hallway', 'foyer', 'entrance', 'family_lounge', 'living_room'}}
        floor_graph = {r.room_id: graph[r.room_id] & {b.room_id for b in design.rooms if b.floor == floor}
                       for r in design.rooms if r.floor == floor}
        for stair in stairs:
            starts_here = landings & graph[stair.room_id]
            if not starts_here:
                failures.append({'code': 'STAIR_ACCESS_POOR', 'room_id': stair.room_id})
            for room in (r for r in design.rooms if r.floor == floor and r != stair):
                blocked = (private - {room.room_id}) | {stair.room_id}
                if not any(room.room_id in reachable(floor_graph, start, blocked) for start in starts_here):
                    failures.append({'code': 'UPPER_CIRCULATION_DISCONNECTED', 'room_id': room.room_id})
    return failures


def requires_circulation(design, geometry, quality):
    """Try existing access first; reserve only for observed access/zoning failures."""
    if circulation_failures(design):
        return True
    return bool(set(geometry.failed_rules) & {'privacy_access', 'accessibility', 'disconnected_layout'} or
                set(quality.failures if quality else ()) &
                {'bathroom_circulation_access', 'bedroom_public_privacy', 'long_hallway',
                 'excessive_circulation', 'bedroom_spine', 'public_zone_separation'})


def _minimum(intent):
    rule = rule_for(intent.type)
    return max(intent.min_area_sqft, rule.min_width * rule.min_length)


def _slice_bank(intents, width, depth, stats=None):
    """Small bounded guillotine constraint search, returning local rectangles."""
    nodes = 0
    by_id = {r.id: r for r in intents}

    @lru_cache(maxsize=MAX_SLICE_NODES)
    def solve(ids, w, h):
        nonlocal nodes
        if nodes >= MAX_SLICE_NODES or (stats is not None and stats['slice_nodes'] >= MAX_RESERVATION_NODES):
            return None
        nodes += 1
        if stats is not None:
            stats['slice_nodes'] += 1
        rs = [by_id[i] for i in ids]
        area = w * h
        lower = sum(_minimum(r) for r in rs)
        upper = sum(max(_minimum(r), r.target_area_sqft * 1.25) for r in rs)
        if area < lower - .01 or area > upper + .01:
            return None
        if len(rs) == 1:
            r = rs[0]
            rule = rule_for(r.type)
            a, b = sorted((w, h))
            m, n = sorted((rule.min_width, rule.min_length))
            if a < m - .001 or b < n - .001 or b / a > min(rule.aspect_limit, 2.25) + .00001:
                return None
            return ((r.id, 0., 0., w, h),)
        # Contiguous splits of several deterministic orders avoid factorial search.
        orders = [ids, tuple(sorted(ids, key=lambda i: (-by_id[i].target_area_sqft, i))),
                  tuple(sorted(ids, key=lambda i: (room_kind(by_id[i].type), i)))]
        seen = set()
        for order in orders:
            for index in range(1, len(order)):
                left, right = order[:index], order[index:]
                if (left, right) in seen:
                    continue
                seen.add((left, right))
                left_target = sum(max(_minimum(by_id[i]), by_id[i].target_area_sqft) for i in left)
                total_target = left_target + sum(max(_minimum(by_id[i]), by_id[i].target_area_sqft) for i in right)
                for axis in (0, 1):
                    span, other = (w, h) if axis == 0 else (h, w)
                    ideal = span * left_target / total_target
                    lower_cut = sum(_minimum(by_id[i]) for i in left) / other
                    upper_cut = span - sum(_minimum(by_id[i]) for i in right) / other
                    cuts = [ideal, ceil(ideal), int(ideal), lower_cut, upper_cut]
                    for group, reverse in ((left, False), (right, True)):
                        if len(group) == 1:
                            rule = rule_for(by_id[group[0]].type)
                            for edge in (rule.min_width, rule.min_length, other / min(rule.aspect_limit, 2.25)):
                                cuts.append(span-edge if reverse else edge)
                    for cut in dict.fromkeys(round(c, 6) for c in cuts):
                        if stats is not None and stats['slice_nodes'] >= MAX_RESERVATION_NODES:
                            return None
                        if not 0 < cut < span:
                            continue
                        aw, ah = (cut, h) if axis == 0 else (w, cut)
                        bw, bh = (w-cut, h) if axis == 0 else (w, h-cut)
                        first = solve(left, round(aw, 6), round(ah, 6))
                        if first is None:
                            continue
                        second = solve(right, round(bw, 6), round(bh, 6))
                        if second is not None:
                            dx, dy = (cut, 0) if axis == 0 else (0, cut)
                            return first + tuple((i, x+dx, y+dy, rw, rh) for i,x,y,rw,rh in second)
        return None

    result = solve(tuple(r.id for r in intents), round(width, 6), round(depth, 6))
    return result


def _floor_options(rooms, hall_width, stair_width, hall_depth, entrance_id=None, adjacencies=(), stats=None):
    if len(rooms) > MAX_BANK_ROOMS or len(rooms) < 2:
        return []
    options = []
    partitions = 0
    # Public front / private rear is preferred but private frontage is allowed.
    ordered = sorted(rooms, key=lambda r: (r.id != entrance_id, room_kind(r.type) in PRIVATE, r.id))
    for count in range(1, len(rooms)):
        for front in combinations(ordered, count):
            if entrance_id and not any(r.id == entrance_id for r in front):
                continue
            partitions += 1
            if partitions > MAX_FLOOR_PARTITIONS:
                break
            front_ids = {r.id for r in front}
            back = [r for r in ordered if r.id not in front_ids]
            for scale in (1.0, .9, .8, 1.12, 1.24):
                if stats is not None and stats['slice_nodes'] >= MAX_RESERVATION_NODES:
                    break
                fw = hall_width + stair_width
                fd = sum(max(_minimum(r), r.target_area_sqft * scale) for r in front) / fw
                bd = sum(max(_minimum(r), r.target_area_sqft * scale) for r in back) / hall_width
                f = _slice_bank(front, fw, fd, stats)
                b = _slice_bank(back, hall_width, bd, stats)
                if f is None or b is None:
                    continue
                # Each private room must touch the strip, not another bedroom.
                if any(room_kind(next(r.type for r in front if r.id == i)) in PRIVATE and
                       (abs(y+h-fd) > .001 or min(x+w, hall_width)-x < 3)
                       for i,x,y,w,h in f):
                    continue
                if any(room_kind(next(r.type for r in back if r.id == i)) in PRIVATE and y > .001
                       for i,x,y,w,h in b):
                    continue
                area = fw*fd + hall_width*bd
                void = stair_width * max(0, hall_depth + bd - 10)
                score = void + abs(fd-bd)*2 + abs(scale-1)*area
                rects = {i: (x,y,w,h) for i,x,y,w,h in f}
                rects.update({i: (x,y+fd+hall_depth,w,h) for i,x,y,w,h in b})
                for adj in adjacencies:
                    if adj.priority != 'HIGH' or adj.relationship != 'ADJACENT':
                        continue
                    if adj.room_a not in rects or adj.room_b not in rects:
                        continue
                    x,y,w,h = rects[adj.room_a]
                    bx,by,bw,bh = rects[adj.room_b]
                    touches = ((abs(x+w-bx)<.001 or abs(bx+bw-x)<.001) and min(y+h,by+bh)-max(y,by)>=3-.001 or
                               (abs(y+h-by)<.001 or abs(by+bh-y)<.001) and min(x+w,bx+bw)-max(x,bx)>=3-.001)
                    if not touches:
                        score += 10000
                options.append((score, f, b, fd, bd, tuple(front), tuple(back), scale))
            if stats is not None and stats['slice_nodes'] >= MAX_RESERVATION_NODES:
                break
        if partitions > MAX_FLOOR_PARTITIONS or (stats is not None and stats['slice_nodes'] >= MAX_RESERVATION_NODES):
            break
    ordered = sorted(options, key=lambda o: (o[0], o[3], tuple(r[0] for r in o[1])))
    # Keep area ranks represented: small footprints must not crowd out the
    # slightly larger rooms needed to stay below the circulation-area limit.
    retained = []
    for scale in (1., .9, .8, 1.12, 1.24):
        retained.extend([o for o in ordered if o[7] == scale][:4])
    return sorted(retained, key=lambda o: (o[0], o[3]))[:MAX_FLOOR_OPTIONS]


def reserved_layouts(program, plot, stats=None):
    """Yield at most three complete circulation-aware placements, no finishing.

    A short hallway also serves as the upper landing. Existing hallway/foyer
    intent is reused; generated space is explicitly attributed to Python.
    """
    from app.design.geometry.geometry_generator import LayoutSolver, PlacedRoom, _normalize_room_type

    side = plot.effective_entrance_side
    env_w, env_l = plot.buildable_width, plot.buildable_length
    if side in {'east', 'west'}:
        env_w, env_l = env_l, env_w
    normalized = program.model_copy(deep=True)
    for intent in normalized.rooms:
        intent.type = _normalize_room_type(intent.type)
    hall_rule = rule_for('hallway')
    stair_rule = rule_for('staircase')
    sw = stair_rule.min_width if program.floor_count > 1 else 0
    explicit = {}
    floor_rooms = {}
    for floor in range(1, program.floor_count+1):
        candidates = [r for r in normalized.rooms if r.floor == floor and room_kind(r.type) in {'hallway', 'foyer', 'entrance'}]
        explicit[floor] = candidates[0] if candidates else None
        floor_rooms[floor] = [r for r in normalized.rooms if r.floor == floor and r != explicit[floor]
                              and room_kind(r.type) != 'staircase']
    hd = max([hall_rule.min_width] + [rule_for(r.type).min_width for r in explicit.values() if r])
    used_ids = {r.id for r in program.rooms}
    def fresh(base):
        while base in used_ids:
            base += '_generated'
        used_ids.add(base)
        return base
    hall_ids = {f: explicit[f].id if explicit[f] else fresh(f'circulation_{f}') for f in floor_rooms}
    stair_ids = {f: next((r.id for r in normalized.rooms if r.floor == f and room_kind(r.type) == 'staircase'), None)
                or fresh(f'staircase_{f}') for f in floor_rooms}

    stats = {'slice_nodes': 0} if stats is None else stats
    for hw in (20., 22., 23.):
        if stats['slice_nodes'] >= MAX_RESERVATION_NODES:
            break
        if hw + sw > env_w:
            continue
        if any(r and not r.min_area_sqft <= hw*hd <= r.target_area_sqft*1.25 for r in explicit.values()):
            continue
        opts = {f: _floor_options(rs, hw, sw, hd, program.entrance.connect_to if f == 1 else None, program.adjacencies, stats)
                for f, rs in floor_rooms.items()}
        if any(not o for o in opts.values()):
            continue
        found = None
        for ground in opts[1]:
            uppers = opts.get(2, [None])
            for upper in uppers:
                fd = max(ground[3], upper[3] if upper else 0)
                bd = max(ground[4], upper[4] if upper else 0)
                if fd + max(hd+bd, stair_rule.min_length if sw else 0) > env_l:
                    continue
                # Ground fills both banks to support every upper room; rebuild
                # against the shared core rather than shifting a finished plan.
                gf = _slice_bank(ground[5], hw+sw, fd, stats)
                gb = _slice_bank(ground[6], hw, bd, stats)
                if gf is None or gb is None:
                    continue
                inset = min(4., *(x+w-3 for _,x,y,w,h in gf if abs(y+h-fd) < .001),
                            *(x+w-3 for _,x,y,w,h in gb if abs(y) < .001))
                if upper:
                    inset = min(inset, *(x+w-3 for _,x,y,w,h in upper[1] if abs(y+h-upper[3]) < .001),
                                *(x+w-3 for _,x,y,w,h in upper[2] if abs(y) < .001))
                inset = max(0., inset) if sw else 0.
                circ = ((hw-inset)*hd + sw*stair_rule.min_length) * program.floor_count
                usable = (hw+sw)*fd + hw*bd
                if upper:
                    usable += (hw+sw)*upper[3] + hw*upper[4]
                if circ/(usable+circ) > QUALITY.circulation_reject:
                    continue
                if not any(explicit.values()) and hw-inset > QUALITY.hallway_preferred_ft:
                    continue
                found = (ground, upper, fd, bd, gf, gb, inset)
                break
            if found:
                break
        if not found:
            continue
        ground, upper, fd, bd, gf, gb, inset = found
        placed, ownership = [], []
        for floor in floor_rooms:
            option = ground if floor == 1 else upper
            front = gf if floor == 1 else option[1]
            back = gb if floor == 1 else option[2]
            intents = {r.id: r for r in floor_rooms[floor]}
            for bank, dy in ((front, 0 if floor == 1 else fd-option[3]), (back, fd+hd)):
                for rid,x,y,w,h in bank:
                    placed.append(PlacedRoom(rid, intents[rid].type, floor, x, y+dy, w, h, intents[rid].target_area_sqft))
            intent = explicit[floor]
            # Reserve only the frontage needed by the connections. All bank
            # rooms along the strip retain at least a 3 ft shared wall.
            placed.append(PlacedRoom(hall_ids[floor], intent.type if intent else 'hallway', floor, inset, fd, hw-inset, hd, (hw-inset)*hd))
            if not intent:
                ownership.append({'room_id': hall_ids[floor], 'floor': floor, 'generated_reason': 'CIRCULATION_REQUIRED',
                                  'owner': 'PYTHON', 'role': 'landing_hallway' if floor > 1 else 'hallway'})
            if sw:
                placed.append(PlacedRoom(stair_ids[floor], 'staircase', floor, hw, fd, sw, stair_rule.min_length, sw*stair_rule.min_length))
        # Rotate the raw solved geometry into the requested site orientation.
        for r in placed:
            x,y,w,h = r.x,r.y,r.width,r.length
            if side == 'north':
                r.x, r.y = env_w-x-w, env_l-y-h
            elif side == 'east':
                r.x,r.y,r.width,r.length = env_l-y-h,x,h,w
            elif side == 'west':
                r.x,r.y,r.width,r.length = y,env_w-x-w,h,w
        solver = LayoutSolver(program, plot)
        design, metadata = solver._build_result(placed, validate=False)
        metadata['generated_circulation'] = ownership
        metadata['repair_strategy'] = 'RESERVE_CIRCULATION_BEFORE_PLACEMENT'
        metadata['reservation_width'] = hw
        metadata['reservation_slice_nodes'] = stats['slice_nodes']
        yield design, metadata
