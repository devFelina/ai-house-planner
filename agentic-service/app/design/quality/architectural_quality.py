"""Deterministic residential quality gate, independent of geometry certification."""

import itertools
import logging
from dataclasses import asdict, dataclass
from heapq import heappop, heappush
from math import hypot, inf

from app.design.geometry.adjacency import exterior_segments, graph_for, shared_wall
from app.design.quality.quality_config import QUALITY, WEIGHTS
from app.design.quality.quality_metrics import calculate_quality_metrics
from app.design.program.room_rules import CIRCULATION_TYPES, room_kind

logger = logging.getLogger(__name__)

PUBLIC = {'living_room', 'dining', 'kitchen'}
OUTDOOR = {'balcony', 'veranda'}


@dataclass
class QualityResult:
    passed: bool
    status: str
    score: float
    failures: list[str]
    metrics: dict
    score_breakdown: dict

    def to_dict(self):
        return asdict(self)


def centre(room):
    return room.x + room.width / 2, room.y + room.length / 2


def travel_distances(design):
    graph = graph_for(design.rooms, design.connections)
    by_id = {room.room_id: room for room in design.rooms}
    all_dist = {}
    for start in graph:
        distances, queue = {start: 0.0}, [(0.0, start)]
        while queue:
            distance, node = heappop(queue)
            if distance > distances[node]:
                continue
            for other in graph[node]:
                a, b = by_id[node], by_id[other]
                ax, ay = centre(a)
                bx, by = centre(b)
                cost = abs(ax - bx) + abs(ay - by) + 12 * abs(a.floor - b.floor)
                if distance + cost < distances.get(other, inf):
                    distances[other] = distance + cost
                    heappush(queue, (distance + cost, other))
        all_dist[start] = distances
    return all_dist


def _topology_geometry(design):
    rooms = [room for room in design.rooms if room.floor == 1 and room_kind(room.room_type) not in OUTDOOR]
    if not rooms:
        return False, {}
    xs = sorted({value for room in rooms for value in (room.x, room.x + room.width)})
    ys = sorted({value for room in rooms for value in (room.y, room.y + room.length)})
    if len(xs) < 2 or len(ys) < 2:
        return False, {}

    cells = {
        (i, j)
        for i in range(len(xs) - 1)
        for j in range(len(ys) - 1)
        if any(
            room.x <= (xs[i] + xs[i + 1]) / 2 <= room.x + room.width
            and room.y <= (ys[j] + ys[j + 1]) / 2 <= room.y + room.length
            for room in rooms
        )
    }
    concave = [
        (i, j)
        for i in range(len(xs))
        for j in range(len(ys))
        if sum((a, b) in cells for a, b in ((i - 1, j - 1), (i, j - 1), (i - 1, j), (i, j))) == 3
    ]
    width, height = xs[-1] - xs[0], ys[-1] - ys[0]
    aspect = max(width, height) / max(min(width, height), 0.01)
    density = sum(room.width * room.length for room in rooms) / max(width * height, 0.01)
    useful = [room for room in rooms if room_kind(room.room_type) in PUBLIC | {'bedroom', 'home_office', 'family_lounge'}]
    corridor_only = [room for room in rooms if room_kind(room.room_type) in CIRCULATION_TYPES]
    cross_sections_x = all(any(room.x < (a + b) / 2 < room.x + room.width for room in useful) for a, b in itertools.pairwise(xs))
    cross_sections_y = all(any(room.y < (a + b) / 2 < room.y + room.length for room in useful) for a, b in itertools.pairwise(ys))
    meaningful = cross_sections_x and cross_sections_y
    broad_wings = all(min(xs[i] - xs[0], xs[-1] - xs[i], ys[j] - ys[0], ys[-1] - ys[j]) >= 8 for i, j in concave)
    family = design.template_family or ''
    hall_penalty = max((max(room.width, room.length) for room in corridor_only if room_kind(room.room_type) == 'hallway'), default=0.0)

    valid = False
    if family == 'COMPACT_RECTANGLE':
        valid = density >= 0.90 and aspect <= 1.8 and not concave and hall_penalty <= QUALITY.hallway_preferred_ft
    elif family == 'LINEAR':
        valid = density >= 0.88 and 1.8 < aspect <= 2.8 and not concave and hall_penalty <= QUALITY.hallway_max_ft
    elif family == 'L_SHAPE':
        valid = len(concave) == 1 and 0.60 <= density <= 0.94 and meaningful and broad_wings
    elif family == 'T_SHAPE':
        valid = len(concave) == 2 and meaningful and broad_wings and aspect <= 2.8
    elif family == 'CENTRAL_CORE':
        cores = [room for room in corridor_only if room_kind(room.room_type) in CIRCULATION_TYPES]
        valid = density >= 0.88 and aspect <= 2.0 and any(
            abs(centre(room)[0] - (xs[0] + width / 2)) < width * 0.25
            and abs(centre(room)[1] - (ys[0] + height / 2)) < height * 0.25
            and len({shared_wall(room, other)[0] for other in useful if shared_wall(room, other)}) >= 3
            for room in cores
        )
    elif family == 'SPLIT_ZONE':
        public = [room for room in rooms if room_kind(room.room_type) in PUBLIC]
        private = [room for room in rooms if room_kind(room.room_type) == 'bedroom']
        separated = public and private and (
            max(room.y + room.length for room in public) <= min(room.y for room in private)
            or max(room.x + room.width for room in public) <= min(room.x for room in private)
        )
        valid = bool(separated) and meaningful and any(
            room_kind(room.room_type) in CIRCULATION_TYPES and max(room.width, room.length) <= 16 for room in rooms
        )
    elif family in {'DUPLEX_STACKED', 'HILLSIDE_STEPPED', 'COASTAL_RAISED_COMPACT'}:
        valid = density >= 0.80 and aspect <= 2.6

    return bool(valid), {
        'concave_corners': len(concave),
        'footprint_aspect': round(aspect, 3),
        'footprint_density': round(density, 3),
        'topology_family_valid': bool(valid),
    }


def _preference_failures(design, req, plot=None):
    failures = []
    rooms = design.rooms
    kinds = [room_kind(room.room_type) for room in rooms]
    if kinds.count('bedroom') != req.bedrooms:
        failures.append('preference_bedroom_count')
    if kinds.count('bathroom') < req.bathrooms:
        failures.append('preference_bathroom_count')
    if {room.floor for room in rooms} != set(range(1, req.floors + 1)) or design.floor_count != req.floors:
        failures.append('preference_floor_count')
    for required, kind in [
        (req.home_office, 'home_office'),
        (req.utility_room, 'utility'),
        (req.balcony, 'balcony'),
        (req.veranda, 'veranda'),
        (req.dining_required, 'dining'),
    ]:
        if required and kind not in kinds:
            failures.append(f'preference_{kind}')

    graph = graph_for(rooms, design.connections)
    stairs = [room for room in rooms if room_kind(room.room_type) == 'staircase']
    if req.floors == 1 and stairs:
        failures.append('program_stair_forbidden_single_floor')
    if req.floors > 1:
        for floor in range(1, req.floors + 1):
            floor_stairs = [room for room in stairs if room.floor == floor]
            if not floor_stairs:
                failures.append('program_stair_required')
            if floor > 1 and floor_stairs and not any(
                any(other.floor == floor and room_kind(other.room_type) in
                    {'hallway', 'foyer', 'family_lounge', 'living_room'} and
                    other.room_id in graph.get(stair.room_id, set()) for other in rooms)
                for stair in floor_stairs
            ):
                failures.append('program_upper_landing_connection')
    if getattr(req, 'attached_bathroom', False) or getattr(req, 'master_bedroom', False):
        master = next((room for room in rooms if room.room_type == 'bedroom_1'), None)
        attached = [room for room in rooms if room.room_type == 'bathroom_attached']
        if not master or not any(graph.get(bath.room_id) == {master.room_id} for bath in attached):
            failures.append('preference_master_ensuite')
    if req.open_plan and not any(connection.kind == 'open' for connection in design.connections):
        failures.append('preference_open_plan')
    if req.accessibility:
        ground = {room_kind(room.room_type) for room in rooms if room.floor == 1}
        if not {'bedroom', 'bathroom'} <= ground or any(
            min(room.width, room.length) < 3.5 for room in rooms
            if room.floor == 1 and room_kind(room.room_type) == 'hallway'
        ):
            failures.append('preference_accessibility')
    for balcony in [room for room in rooms if room_kind(room.room_type) == 'balcony']:
        attached = any(other.floor == balcony.floor and room_kind(other.room_type) not in OUTDOOR
                       and other.room_id in graph.get(balcony.room_id, set()) for other in rooms)
        if req.floors < 2 or balcony.floor == 1 or not attached or not exterior_segments(balcony, rooms):
            failures.append('program_balcony')
    for veranda in [room for room in rooms if room_kind(room.room_type) == 'veranda']:
        if veranda.floor != 1 or not exterior_segments(veranda, rooms):
            failures.append('program_veranda')
    if req.utility_room:
        utilities = [room for room in rooms if room_kind(room.room_type) == 'utility']
        kitchens = [room for room in rooms if room_kind(room.room_type) == 'kitchen']
        if not utilities or not kitchens or not any(
            kitchen.room_id in graph.get(utility.room_id, set()) or
            hypot(centre(utility)[0] - centre(kitchen)[0], centre(utility)[1] - centre(kitchen)[1]) <= 20
            for utility in utilities for kitchen in kitchens
        ):
            failures.append('preference_utility_service_zone')
    if req.parking:
        valid = False
        if plot:
            for space in design.site_features:
                if space.get('type') != 'parking' or space.get('road_side') != plot.road_side:
                    continue
                x, y, width, length = (space.get(key, 0) for key in ('x', 'y', 'width', 'length'))
                on_road = {
                    'south': abs(y) < 0.01,
                    'north': abs(y + length - plot.plot_length_ft) < 0.01,
                    'west': abs(x) < 0.01,
                    'east': abs(x + width - plot.plot_width_ft) < 0.01,
                }[plot.road_side]
                overlap = any(
                    min(x + width, room.x + plot.edge_setbacks['west'] + room.width) > max(x, room.x + plot.edge_setbacks['west'])
                    and min(y + length, room.y + plot.edge_setbacks['south'] + room.length) > max(y, room.y + plot.edge_setbacks['south'])
                    for room in rooms if room.floor == 1
                )
                valid |= min(width, length) >= 9 and max(width, length) >= 18 and on_road and not overlap and x >= 0 and y >= 0 and x + width <= plot.plot_width_ft and y + length <= plot.plot_length_ft
        if not valid:
            failures.append('preference_parking')
    return failures


def validate_architectural_quality(design, req=None, plot=None, config=QUALITY):
    if not design.rooms:
        return QualityResult(False, 'ARCHITECTURALLY_POOR', 0, ['no_rooms'], {}, {})

    metrics = calculate_quality_metrics(design)
    internal = [room for room in design.rooms if room_kind(room.room_type) not in OUTDOOR]
    area = sum(room.width * room.length for room in internal)
    circulation_area = sum(room.width * room.length for room in internal if room_kind(room.room_type) in CIRCULATION_TYPES)
    ratio = circulation_area / max(area, 1)
    metrics['circulation_ratio'] = round(ratio, 4)

    failures = []
    if ratio > config.circulation_reject:
        failures.append('excessive_circulation')

    graph = graph_for(design.rooms, design.connections)
    halls = []
    for room in internal:
        if room_kind(room.room_type) != 'hallway':
            continue
        width, length = sorted((room.width, room.length))
        floor_rooms = [other for other in internal if other.floor == room.floor]
        span = max(
            max(other.x + other.width for other in floor_rooms) - min(other.x for other in floor_rooms),
            max(other.y + other.length for other in floor_rooms) - min(other.y for other in floor_rooms),
        )
        ends = {door.wall for door in room.doors} & ({'north', 'south'} if room.length >= room.width else {'east', 'west'})
        side_doors = [door.offset + door.width / 2 for door in room.doors if door.wall not in ({'north', 'south'} if room.length >= room.width else {'east', 'west'})]
        dead_end = max(0, length - max(side_doors, default=0)) if len(ends) < 2 else 0
        dependency_count = len(graph.get(room.room_id, set()))
        halls.append({'width': width, 'length': length, 'aspect_ratio': round(length / max(width, 0.01), 3), 'dead_end_length': round(dead_end, 2), 'dependent_rooms': dependency_count})
        if (
            length > config.hallway_max_ft
            or length / max(width, 0.01) > config.hallway_max_aspect
            or length / max(span, 0.01) > config.hallway_max_footprint_fraction
            or dead_end > config.dead_end_max_ft
            or (dependency_count >= 4 and length > config.hallway_preferred_ft)
        ):
            failures.append('long_hallway')
    metrics['hallways'] = halls

    distances = travel_distances(design)
    dist = lambda a, b: distances.get(a.room_id, {}).get(b.room_id, inf)
    rooms = design.rooms
    beds = [room for room in rooms if room_kind(room.room_type) == 'bedroom']
    baths = [room for room in rooms if room_kind(room.room_type) == 'bathroom' and room.room_type != 'bathroom_attached']
    living = [room for room in rooms if room_kind(room.room_type) == 'living_room']
    kitchen = [room for room in rooms if room_kind(room.room_type) == 'kitchen']
    dining = [room for room in rooms if room_kind(room.room_type) == 'dining']
    public = living + dining + kitchen

    public_distance = max((min(dist(l, k) for k in kitchen) for l in living), default=inf) if kitchen and living else inf
    if dining:
        public_distance = max(public_distance, max(min(dist(d, room) for room in kitchen + living) for d in dining))
    elif living and kitchen:
        public_distance = min(public_distance, max(min(dist(l, k) for k in kitchen) for l in living))
    if public_distance > config.public_travel_max_ft:
        failures.append('public_zone_separation')

    bed_distance = max((dist(a, b) for i, a in enumerate(beds) for b in beds[i + 1:] if a.floor == b.floor), default=0)
    logger.debug('bed_distance=%.1f max=%.1f', bed_distance, config.bedroom_travel_max_ft)
    if bed_distance > config.bedroom_travel_max_ft:
        failures.append('bedroom_spine')

    bedroom_cluster_distance = metrics['bathroom_cluster_distance_ft']
    if bedroom_cluster_distance > 24:
        failures.append('remote_bathrooms')

    if any(not any(room_kind(room.room_type) in CIRCULATION_TYPES and room.room_id in graph.get(bath.room_id, set()) for room in rooms) for bath in baths):
        failures.append('bathroom_circulation_access')

    entrance_distance = inf
    for entrance in design.entrances:
        room = next((room for room in rooms if room.room_id == entrance.room_id), None)
        if room:
            entrance_distance = min(entrance_distance, min((dist(room, room2) for room2 in public), default=inf))
            if room_kind(room.room_type) not in PUBLIC | {'foyer', 'entrance'}:
                failures.append('private_or_corridor_entrance')
    if entrance_distance > config.entrance_public_max_ft:
        failures.append('remote_entrance')

    wet = metrics['wet_average_distance_ft']
    if wet > config.wet_core_max_ft:
        failures.append('dispersed_wet_core')
    compact = metrics['compactness_ratio']
    if compact < config.minimum_compactness:
        failures.append('wasted_voids')
    if metrics['unused_internal_void_area'] > area * 0.18:
        failures.append('unnecessary_voids')
    if metrics['extreme_room_proportions']:
        failures.append('poor_room_proportions')

    topology_valid, topology_metrics = _topology_geometry(design)
    metrics.update(topology_metrics)
    if not topology_valid:
        failures.append('topology_mismatch')

    private_edges = sum(any(bed.room_id in graph.get(room.room_id, set()) for room in living + kitchen) for bed in beds)
    if private_edges:
        failures.append('bedroom_public_privacy')

    preference = _preference_failures(design, req, plot) if req else []
    failures.extend(preference)

    def proximity(value, good, limit):
        if value == inf:
            return 0
        if value <= good:
            return 100
        return max(0, min(100, 100 - 50 * max(0, value - good) / max(limit - good, 1)))

    bedroom_private_distance = max((dist(bed, room) for i, bed in enumerate(beds) for room in beds[i + 1:] if bed.floor == room.floor), default=0)
    scores = {
        'circulation_efficiency': proximity(ratio, config.circulation_excellent, config.circulation_reject),
        'compactness': min(100, compact * 110),
        'public_zone_quality': proximity(public_distance, 12, config.public_travel_max_ft),
        'private_zone_quality': proximity(bedroom_private_distance, 18, config.bedroom_travel_max_ft),
        'wet_core_quality': proximity(wet, 16, config.wet_core_max_ft),
        'entrance_quality': proximity(entrance_distance, 0, config.entrance_public_max_ft),
        'privacy': max(0, 100 - private_edges * 35),
        'topology_fidelity': 100 if topology_valid else 0,
        'preference_match': 0 if preference else 100,
    }
    score = round(sum(scores[key] * weight for key, weight in WEIGHTS.items()), 2)
    if score < config.minimum_score:
        failures.append('minimum_quality_score')
    if failures:
        score = min(score, config.hard_failure_score_cap)

    metrics.update(
        public_zone_travel_ft=public_distance if public_distance < inf else None,
        bedroom_travel_ft=bed_distance if bed_distance < inf else None,
        bathroom_travel_ft=bedroom_cluster_distance if bedroom_cluster_distance < inf else None,
        entrance_to_public_zone_distance=entrance_distance if entrance_distance < inf else None,
        privacy_score=scores['privacy'],
        preference_match=scores['preference_match'],
        public_zone_score=scores['public_zone_quality'],
        wet_core_score=scores['wet_core_quality'],
        topology_fidelity_score=scores['topology_fidelity'],
        compactness_score=scores['compactness'],
    )
    return QualityResult(not failures, 'VALID_HIGH_QUALITY' if not failures else 'ARCHITECTURALLY_POOR', score, sorted(set(failures)), metrics, scores)
