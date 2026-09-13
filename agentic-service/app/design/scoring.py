"""Deterministic conceptual quality scores, applied only to valid candidates."""
from app.design.adjacency import exterior_segments, graph_for, reachable, shared_wall
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints
from app.design.room_rules import CIRCULATION_TYPES, room_kind
from app.design.quality_metrics import calculate_quality_metrics
from app.schemas.design_result import DesignResult

SCORE_WEIGHTS = {
    'circulation_efficiency': 20,
    'adjacency_quality': 15,
    'privacy_zoning': 15,
    'room_proportion_quality': 15,
    'plot_utilisation': 10,
    'exterior_wall_opportunities': 10,
    'terrain_suitability': 10,
    'preference_match': 5,
}


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
                 plot: PlotConstraints) -> tuple[float, dict]:
    rooms = layout.rooms
    total = sum(r.width*r.length for r in rooms)
    quality = calculate_quality_metrics(layout)
    graph = graph_for(rooms, layout.connections)
    start = layout.entrances[0].room_id
    ratio = quality['circulation_ratio']
    circulation = 1.0 if ratio <= 0.08 else max(0, 1-(ratio-0.08)/0.10)
    circulation -= min(0.35, quality['dead_end_hallways'] * 0.15 + quality['single_use_hallways'] * 0.08)
    circulation -= max(0, quality['longest_hallway_ft']-20) / 40
    by_type = {r.room_type: r for r in rooms}
    adjacency_scores = []
    for a, b, strength in (layout.program or {}).get('adjacency_preferences', []):
        if a not in by_type or b not in by_type:
            continue
        ra, rb = by_type[a], by_type[b]
        distance = abs(ra.x+ra.width/2-rb.x-rb.width/2)+abs(ra.y+ra.length/2-rb.y-rb.length/2)+20*abs(ra.floor-rb.floor)
        proximity = 1.0 if shared_wall(ra, rb) else max(0, 1-distance/60)
        adjacency_scores.append(1-proximity if strength == 'discouraged' else proximity)
    wet_zone_efficiency = max(0, 1-quality['wet_average_distance_ft']/45)
    bathroom_placement = max(0, 1-quality['bathroom_cluster_distance_ft']/35)
    adjacency = (sum(adjacency_scores)/max(1, len(adjacency_scores)) * 0.6 +
                 wet_zone_efficiency * 0.2 + bathroom_placement * 0.2)
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
    proportion = max(0, 1-quality['extreme_room_proportions']/max(1, len(rooms)))
    target_coverage = 0.25 if requirements.garden_priority else 0.5
    usage = (layout.ground_footprint_sqft or 0)/plot.maximum_ground_footprint
    utilisation = max(0, 1-abs(usage-target_coverage))
    affinity = family_affinity(layout.template_family or '', requirements, plot)
    terrain = affinity if plot.terrain_type != 'flat' else 1.0
    metrics = {
        'circulation_efficiency': circulation,
        'adjacency_quality': adjacency,
        'privacy_zoning': privacy,
        'room_proportion_quality': proportion,
        'plot_utilisation': utilisation,
        'exterior_wall_opportunities': quality['exterior_wall_ratio'],
        'terrain_suitability': terrain,
        'preference_match': affinity,
    }
    parts = {k: round(max(0, min(1, v))*SCORE_WEIGHTS[k], 3) for k, v in metrics.items()}
    parts['circulation_efficiency_score'] = round(max(0, min(1, circulation)) * 100, 2)
    parts['wet_zone_efficiency_score'] = round(wet_zone_efficiency * 100, 2)
    parts['exterior_wall_score'] = round(quality['exterior_wall_ratio'] * 100, 2)
    parts['quality_metrics'] = quality
    weighted_total = sum(parts[key] for key in SCORE_WEIGHTS)
    return round(weighted_total, 2), parts
