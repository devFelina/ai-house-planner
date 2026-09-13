"""Deterministic conceptual quality scores, applied only to valid candidates."""
from app.design.adjacency import exterior_segments, graph_for, reachable, shared_wall
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.room_rules import CIRCULATION_TYPES, room_kind
from app.schemas.design_result import DesignResult

SCORE_WEIGHTS = {'circulation': 25, 'adjacency': 20, 'privacy': 15, 'efficiency': 15,
                 'plot_utilisation': 10, 'terrain': 10, 'preferences': 5}


def family_affinity(family: str, req: Requirements, plot: PlotConstraints) -> float:
    if plot.terrain_type == 'hillside':
        return 1.0 if family == 'HILLSIDE_STEPPED' else 0.5
    if plot.terrain_type == 'coastal':
        return 1.0 if family == 'COASTAL_RAISED_COMPACT' else 0.5
    if min(plot.buildable_width, plot.buildable_length) < 24:
        return 1.0 if family == 'LINEAR' else 0.2
    preferred = set()
    if req.garden_priority or any(word in req.style.lower() for word in ('tropical', 'courtyard')):
        preferred.update(('L_SHAPE', 'T_SHAPE'))
    if req.open_plan or any(word in req.style.lower() for word in ('modern', 'contemporary')):
        preferred.update(('SPLIT_ZONE', 'L_SHAPE'))
    if req.accessibility:
        preferred.add('CENTRAL_CORE')
    if req.compact_priority:
        preferred.update(('COMPACT_RECTANGLE', 'CENTRAL_CORE'))
    if req.privacy_priority:
        preferred.add('SPLIT_ZONE')
    if req.floors > 1:
        preferred.add('DUPLEX_STACKED')
    if not preferred:
        preferred.add('COMPACT_RECTANGLE')
    return 1.0 if family in preferred else 0.2


def score_layout(layout: DesignResult, requirements: Requirements,
                 plot: PlotConstraints) -> tuple[float, dict[str, float]]:
    rooms = layout.rooms
    total = sum(r.width*r.length for r in rooms)
    circ = sum(r.width*r.length for r in rooms if room_kind(r.room_type) in CIRCULATION_TYPES)
    graph = graph_for(rooms, layout.connections)
    start = layout.entrances[0].room_id
    circulation = len(reachable(graph, start))/len(rooms) * max(0, 1-max(0, circ/total-0.16)*2)
    by_type = {r.room_type: r for r in rooms}
    adjacency_scores = []
    for a, b, _ in (layout.program or {}).get('adjacency_preferences', []):
        if a not in by_type or b not in by_type:
            continue
        ra, rb = by_type[a], by_type[b]
        distance = abs(ra.x+ra.width/2-rb.x-rb.width/2)+abs(ra.y+ra.length/2-rb.y-rb.length/2)+20*abs(ra.floor-rb.floor)
        adjacency_scores.append(1.0 if shared_wall(ra, rb) else max(0, 1-distance/60))
    bedrooms = [r for r in rooms if room_kind(r.room_type) == 'bedroom']
    exposed = sum(start in graph[r.room_id] for r in bedrooms)
    # Distance along a hall also protects privacy: an entry at the public end is better.
    entry = next(r for r in rooms if r.room_id == start)
    privacy = sum(min(1, (abs(r.x-entry.x)+abs(r.y-entry.y)+20*abs(r.floor-1))/25) for r in bedrooms)/max(1, len(bedrooms))
    privacy = (privacy + 1-exposed/max(1, len(bedrooms)))/2
    bbox_area = 0.0
    for floor in range(1, layout.floor_count+1):
        rs = [r for r in rooms if r.floor == floor]
        bbox_area += (max(r.x+r.width for r in rs)-min(r.x for r in rs))*(max(r.y+r.length for r in rs)-min(r.y for r in rs))
    light = sum(bool(exterior_segments(r, rooms)) for r in bedrooms)/max(1, len(bedrooms))
    extreme = sum(max(r.width/r.length, r.length/r.width)>2 for r in rooms if room_kind(r.room_type) not in CIRCULATION_TYPES)/len(rooms)
    efficiency = max(0, min(1, total/bbox_area)*0.8+light*0.2-extreme*0.2)
    target_coverage = 0.25 if requirements.garden_priority else 0.5
    usage = (layout.ground_footprint_sqft or 0)/plot.maximum_ground_footprint
    utilisation = max(0, 1-abs(usage-target_coverage))
    affinity = family_affinity(layout.template_family or '', requirements, plot)
    terrain = affinity if plot.terrain_type != 'flat' else 1.0
    metrics = {'circulation': circulation, 'adjacency': sum(adjacency_scores)/max(1, len(adjacency_scores)),
               'privacy': privacy, 'efficiency': efficiency, 'plot_utilisation': utilisation,
               'terrain': terrain, 'preferences': affinity}
    parts = {k: round(max(0, min(1, v))*SCORE_WEIGHTS[k], 3) for k, v in metrics.items()}
    return round(sum(parts.values()), 2), parts
