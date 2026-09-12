"""Shared wall intervals and traversable graphs; touching corners are not doors."""
from collections import deque
from app.design.models import Connection
from app.design.room_rules import CIRCULATION_TYPES, room_kind, MIN_DOOR_WIDTH
from app.schemas.design_result import RoomLayout, Opening

EPS = 0.001
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east'}


def shared_wall(a: RoomLayout, b: RoomLayout) -> tuple[str, float, float] | None:
    if a.floor != b.floor:
        return None
    for wall, edge, other in [('east', a.x+a.width, b.x), ('west', a.x, b.x+b.width)]:
        lo, hi = max(a.y, b.y), min(a.y+a.length, b.y+b.length)
        if abs(edge-other) < EPS and hi-lo >= MIN_DOOR_WIDTH-EPS:
            return wall, lo, hi
    for wall, edge, other in [('north', a.y+a.length, b.y), ('south', a.y, b.y+b.length)]:
        lo, hi = max(a.x, b.x), min(a.x+a.width, b.x+b.width)
        if abs(edge-other) < EPS and hi-lo >= MIN_DOOR_WIDTH-EPS:
            return wall, lo, hi
    return None


def exterior_segments(room: RoomLayout, rooms: list[RoomLayout]) -> list[tuple[str, float, float]]:
    result = []
    for wall in ('north', 'south', 'east', 'west'):
        horizontal = wall in ('north', 'south')
        origin = room.x if horizontal else room.y
        span = room.width if horizontal else room.length
        segments = [(origin, origin+span)]
        for other in rooms:
            if other.room_id == room.room_id or other.floor != room.floor:
                continue
            edge = {'north': room.y+room.length, 'south': room.y, 'east': room.x+room.width, 'west': room.x}[wall]
            other_edge = {'north': other.y, 'south': other.y+other.length, 'east': other.x, 'west': other.x+other.width}[wall]
            if abs(edge-other_edge) > EPS:
                continue
            lo = other.x if horizontal else other.y
            hi = lo + (other.width if horizontal else other.length)
            updated = []
            for start, end in segments:
                if hi <= start or lo >= end:
                    updated.append((start, end))
                else:
                    if lo > start:
                        updated.append((start, lo))
                    if hi < end:
                        updated.append((hi, end))
            segments = updated
        result.extend((wall, lo-origin, hi-origin) for lo, hi in segments if hi-lo >= MIN_DOOR_WIDTH-EPS)
    return result


def graph_for(rooms: list[RoomLayout], connections: list[Connection]) -> dict[str, set[str]]:
    graph = {r.room_id: set() for r in rooms}
    for c in connections:
        if c.from_room in graph and c.to_room in graph:
            graph[c.from_room].add(c.to_room)
            graph[c.to_room].add(c.from_room)
    return graph


def reachable(graph: dict[str, set[str]], start: str, blocked: set[str] | None = None) -> set[str]:
    seen, queue = set(), deque([start])
    while queue:
        key = queue.popleft()
        if key in seen or key in (blocked or set()):
            continue
        seen.add(key)
        queue.extend(graph.get(key, set()) - seen)
    return seen


def build_connections(rooms: list[RoomLayout], open_plan: bool) -> list[Connection]:
    connections = []
    for i, a in enumerate(rooms):
        for b in rooms[i+1:]:
            ak, bk = room_kind(a.room_type), room_kind(b.room_type)
            if ak == bk == 'staircase' and abs(a.floor-b.floor) == 1:
                connections.append(Connection(from_room=a.room_id, to_room=b.room_id, kind='stair'))
                continue
            shared = shared_wall(a, b)
            allowed = (ak in CIRCULATION_TYPES or bk in CIRCULATION_TYPES or
                       {ak, bk} <= {'living_room', 'dining', 'kitchen'} or
                       {a.room_type, b.room_type} == {'bedroom_1', 'bathroom_attached'})
            if not shared or not allowed:
                continue
            wall, lo, hi = shared
            kind = 'open' if open_plan and {ak, bk} <= {'living_room', 'dining', 'kitchen'} else 'door'
            width = min(6, hi-lo) if kind == 'open' else MIN_DOOR_WIDTH
            start = (lo+hi-width)/2
            for room, side in [(a, wall), (b, OPPOSITE[wall])]:
                origin = room.x if side in ('north', 'south') else room.y
                room.doors.append(Opening(wall=side, offset=round(start-origin, 4), width=width))
            connections.append(Connection(from_room=a.room_id, to_room=b.room_id, kind=kind))
    return connections


def road_access_clear(room: RoomLayout, rooms: list[RoomLayout], wall: str,
                      offset: float, width: float = MIN_DOOR_WIDTH) -> bool:
    """Check an unobstructed conceptual straight access strip from door to road.

    This is a plot-level accessibility check, not a driveway/grading design.
    """
    horizontal = wall in ('north', 'south')
    lo = (room.x if horizontal else room.y) + offset
    hi = lo + width
    edge = {'north': room.y+room.length, 'south': room.y,
            'east': room.x+room.width, 'west': room.x}[wall]
    for other in rooms:
        if other.floor != 1 or other.room_id == room.room_id:
            continue
        start = other.x if horizontal else other.y
        end = start + (other.width if horizontal else other.length)
        if min(hi, end) - max(lo, start) <= EPS:
            continue
        obstructs = {'north': other.y+other.length > edge+EPS,
                     'south': other.y < edge-EPS,
                     'east': other.x+other.width > edge+EPS,
                     'west': other.x < edge-EPS}[wall]
        if obstructs:
            return False
    return True
