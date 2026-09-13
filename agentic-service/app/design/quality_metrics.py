"""Deterministic conceptual design-quality metrics; no code-compliance claims."""
from collections import deque
from math import hypot
from typing import Any

from app.design.adjacency import exterior_segments, graph_for
from app.design.room_rules import CIRCULATION_TYPES, room_kind
from app.schemas.design_result import DesignResult, RoomLayout

CIRCULATION_GOOD_RATIO = 0.08
CIRCULATION_ACCEPTABLE_RATIO = 0.12
CIRCULATION_VERY_POOR_RATIO = 0.15
NARROW_PLOT_THRESHOLD_FT = 28.0
HALLWAY_PREFERRED_MAX_LENGTH_FT = 20.0
HALLWAY_EXTREME_LENGTH_FT = 32.0


def _centre(room: RoomLayout) -> tuple[float, float]:
    return room.x + room.width / 2, room.y + room.length / 2


def _distance(a: RoomLayout, b: RoomLayout) -> float:
    ax, ay = _centre(a)
    bx, by = _centre(b)
    return hypot(ax - bx, ay - by) + 20 * abs(a.floor - b.floor)


def _shortest_hops(graph: dict[str, set[str]], start: str) -> dict[str, int]:
    hops, queue = {start: 0}, deque([start])
    while queue:
        current = queue.popleft()
        for neighbour in graph.get(current, set()):
            if neighbour not in hops:
                hops[neighbour] = hops[current] + 1
                queue.append(neighbour)
    return hops


def calculate_quality_metrics(design: DesignResult) -> dict[str, Any]:
    rooms = design.rooms
    total = sum(r.width * r.length for r in rooms)
    circulation_rooms = [r for r in rooms if room_kind(r.room_type) in CIRCULATION_TYPES]
    circulation_area = sum(r.width * r.length for r in circulation_rooms)
    usable_area = total - circulation_area
    bounding_box_area = 0.0
    unused_void = 0.0
    for floor in sorted({r.floor for r in rooms}):
        floor_rooms = [r for r in rooms if r.floor == floor]
        box = ((max(r.x + r.width for r in floor_rooms) - min(r.x for r in floor_rooms)) *
               (max(r.y + r.length for r in floor_rooms) - min(r.y for r in floor_rooms)))
        bounding_box_area += box
        unused_void += max(0.0, box - sum(r.width * r.length for r in floor_rooms))

    graph = graph_for(rooms, design.connections)
    hall_lengths = [max(r.width, r.length) for r in circulation_rooms
                    if room_kind(r.room_type) == 'hallway']
    hall_service_counts = [len(graph.get(r.room_id, set())) for r in circulation_rooms
                           if room_kind(r.room_type) == 'hallway']
    dead_end_hallways = sum(count <= 1 for count in hall_service_counts)
    single_use_hallways = sum(count == 2 for count in hall_service_counts)

    important = [r for r in rooms if room_kind(r.room_type) in
                 {'bedroom', 'living_room', 'kitchen', 'bathroom'}]
    exposed = sum(bool(exterior_segments(r, rooms)) for r in important)
    exterior_ratio = exposed / max(1, len(important))

    wet_rooms = [r for r in rooms if room_kind(r.room_type) in {'kitchen', 'bathroom', 'utility'}]
    wet_distances = [_distance(a, b) for i, a in enumerate(wet_rooms)
                     for b in wet_rooms[i + 1:] if a.floor == b.floor]
    wet_average_distance = sum(wet_distances) / max(1, len(wet_distances))

    bedrooms = [r for r in rooms if room_kind(r.room_type) == 'bedroom']
    common_bathrooms = [r for r in rooms if room_kind(r.room_type) == 'bathroom'
                        and r.room_type != 'bathroom_attached']
    bathroom_cluster_distance = 0.0
    if common_bathrooms and bedrooms:
        bedroom_centre_x = sum(_centre(room)[0] for room in bedrooms) / len(bedrooms)
        bedroom_centre_y = sum(_centre(room)[1] for room in bedrooms) / len(bedrooms)
        bathroom_cluster_distance = min(
            hypot(_centre(bath)[0] - bedroom_centre_x, _centre(bath)[1] - bedroom_centre_y)
            + 20 * min(abs(bath.floor - bedroom.floor) for bedroom in bedrooms)
            for bath in common_bathrooms
        )

    entrance_id = design.entrances[0].room_id if design.entrances else None
    longest_access_chain = max(_shortest_hops(graph, entrance_id).values(), default=0) if entrance_id else 0
    extreme_proportions = sum(
        max(r.width / r.length, r.length / r.width) > 2.25
        for r in rooms if room_kind(r.room_type) not in CIRCULATION_TYPES
    )
    return {
        'usable_room_area': round(usable_area, 2),
        'circulation_area': round(circulation_area, 2),
        'circulation_ratio': round(circulation_area / total if total else 1.0, 4),
        'bounding_box_area': round(bounding_box_area, 2),
        'actual_room_footprint_area': round(total, 2),
        'compactness_ratio': round(total / bounding_box_area if bounding_box_area else 0.0, 4),
        'unused_internal_void_area': round(unused_void, 2),
        'longest_hallway_ft': round(max(hall_lengths, default=0.0), 2),
        'dead_end_hallways': dead_end_hallways,
        'single_use_hallways': single_use_hallways,
        'longest_access_chain': longest_access_chain,
        'wet_average_distance_ft': round(wet_average_distance, 2),
        'bathroom_cluster_distance_ft': round(bathroom_cluster_distance, 2),
        'exterior_wall_ratio': round(exterior_ratio, 4),
        'extreme_room_proportions': extreme_proportions,
    }


def quality_feedback(metrics: dict[str, Any]) -> list[str]:
    feedback = []
    ratio = metrics['circulation_ratio']
    if ratio > CIRCULATION_ACCEPTABLE_RATIO:
        feedback.append(
            f"Circulation area is {metrics['circulation_area']:.1f} sqft of "
            f"{metrics['actual_room_footprint_area']:.1f} sqft ({ratio:.1%}). "
            "Shorten hallways or use a compact shared private lobby."
        )
    if metrics['longest_hallway_ft'] > HALLWAY_PREFERRED_MAX_LENGTH_FT:
        feedback.append(
            f"Longest hallway is {metrics['longest_hallway_ft']:.1f} ft; replace the long spine "
            "with shorter shared circulation where practical."
        )
    if metrics['dead_end_hallways']:
        feedback.append('A dead-end hallway serves too little space; simplify the circulation graph.')
    if metrics['bathroom_cluster_distance_ft'] > 24:
        feedback.append('The common bathroom is far from the bedroom cluster; integrate it with shared private circulation.')
    if metrics['wet_average_distance_ft'] > 28:
        feedback.append('Wet/service rooms are widely separated; group them more closely where practical.')
    if metrics['exterior_wall_ratio'] < 0.75:
        feedback.append('More bedrooms, living, kitchen, or bathroom spaces should reach an exterior wall where feasible.')
    if metrics['extreme_room_proportions']:
        feedback.append('One or more habitable rooms have an unnecessarily narrow proportion.')
    return feedback
