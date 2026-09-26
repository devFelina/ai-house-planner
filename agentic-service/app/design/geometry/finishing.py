from collections import deque
import time

from app.design.geometry.adjacency import shared_wall, exterior_segments, road_access_clear, OPPOSITE
from app.schemas.design_result import DesignResult, Opening, RoomLayout
from app.design.program.spatial_program import SpatialProgram
from app.design.program.models import Connection, Entrance
from app.design.program.room_rules import room_kind

def finish_generative_layout(design: DesignResult, program: SpatialProgram, open_plan: bool = False) -> tuple[DesignResult, dict]:
    t0 = time.time()
    for r in design.rooms:
        r.doors = []
        r.windows = []
    design.connections = []
    design.entrances = []

    meta = {
        "shared_wall_pairs": 0,
        "doors_generated": 0,
        "windows_generated": 0,
        "entrance_room": None,
        "circulation_components": 0,
        "unreachable_rooms": [],
        "high_adjacencies_satisfied": [],
        "high_adjacencies_unsatisfied": [],
        "rooms_with_required_windows": 0,
        "window_requirements_satisfied": 0,
        "finishing_ms": 0,
        "finishing_failures": []
    }

    # Step 6: Shared-Wall Graph
    possible_walls = {}
    for i, a in enumerate(design.rooms):
        for b in design.rooms[i+1:]:
            res = shared_wall(a, b)
            if res:
                possible_walls[(a.room_id, b.room_id)] = res
                possible_walls[(b.room_id, a.room_id)] = (OPPOSITE[res[0]], res[1], res[2])
                meta["shared_wall_pairs"] += 1

    # Place Doors
    doors_to_add = set() # (room_a_id, room_b_id) where a < b
    
    # 1. High priority ADJACENT
    for adj in program.adjacencies:
        if adj.relationship == 'ADJACENT' and adj.priority == 'HIGH':
            a, b = adj.room_a, adj.room_b
            if a > b: a, b = b, a
            if (a, b) in possible_walls:
                doors_to_add.add((a, b))
                meta["high_adjacencies_satisfied"].append((a, b))
            else:
                meta["high_adjacencies_unsatisfied"].append((a, b))

    # 2. Circulation connectivity
    # Ensure all rooms connect to circulation (hallway, entrance, foyer, staircase, living_room, dining)
    circulation_nodes = {r.room_id for r in design.rooms if room_kind(r.room_type) in ['hallway', 'staircase', 'foyer', 'entrance', 'living_room', 'dining']}
    
    def add_door(a_id, b_id):
        if a_id > b_id: a_id, b_id = b_id, a_id
        doors_to_add.add((a_id, b_id))

    for r in design.rooms:
        if r.room_id in circulation_nodes:
            # Connect circulation nodes to each other if they share a wall
            for c in circulation_nodes:
                if c != r.room_id and (r.room_id, c) in possible_walls:
                    add_door(r.room_id, c)
        else:
            # Try to connect to a circulation node
            connected = False
            for c in circulation_nodes:
                if (r.room_id, c) in possible_walls:
                    add_door(r.room_id, c)
                    connected = True
            
            # If not connected to circulation, connect to any other room
            if not connected:
                for other in design.rooms:
                    if other.room_id != r.room_id and (r.room_id, other.room_id) in possible_walls:
                        add_door(r.room_id, other.room_id)
                        connected = True
                        break

    # 3. Vertical Core / Stairs
    stairs = {r.floor: r for r in design.rooms if room_kind(r.room_type) == 'staircase'}
    for floor, stair in stairs.items():
        if floor + 1 in stairs:
            design.connections.append(Connection(from_room=stair.room_id, to_room=stairs[floor+1].room_id, kind='stair'))

    # Add doors physically
    by_id = {r.room_id: r for r in design.rooms}
    for a_id, b_id in doors_to_add:
        a, b = by_id[a_id], by_id[b_id]
        res = possible_walls.get((a_id, b_id))
        if not res: continue
        wall, lo, hi = res
        
        ak, bk = room_kind(a.room_type), room_kind(b.room_type)
        is_open = open_plan and {ak, bk} <= {'living_room', 'dining', 'kitchen', 'family_room', 'family_lounge', 'study', 'home_office'}
        
        width = 6 if is_open and hi - lo >= 6 else 3
        start = (lo + hi - width) / 2
        for room, w in [(a, wall), (b, OPPOSITE[wall])]:
            room.doors.append(Opening(
                wall=w,
                offset=round(start - (room.x if w in ('north', 'south') else room.y), 4),
                width=width
            ))
            meta["doors_generated"] += 1
        design.connections.append(Connection(from_room=a_id, to_room=b_id, kind='open' if is_open else 'door'))

    # Step 10: Entrance Door
    entrance_side = program.entrance.preferred_side.lower() if program.entrance else 'south'
    entrance_target = program.entrance.connect_to if program.entrance else None
    
    candidates = []
    for r in design.rooms:
        if r.floor != 1: continue
        for w, lo, hi in exterior_segments(r, design.rooms):
            if w == entrance_side and road_access_clear(r, design.rooms, w, (lo+hi-3)/2):
                candidates.append((r, w, lo, hi))
                
    if not candidates:
        # Fallback to any exterior wall on floor 1
        for r in design.rooms:
            if r.floor != 1: continue
            for w, lo, hi in exterior_segments(r, design.rooms):
                if road_access_clear(r, design.rooms, w, (lo+hi-3)/2):
                    candidates.append((r, w, lo, hi))

    if candidates:
        if entrance_target:
            best = [c for c in candidates if c[0].room_id == entrance_target or room_kind(c[0].room_type) == room_kind(entrance_target)]
            if best: candidates = best
            
        r, wall, lo, hi = candidates[0]
        offset = (lo + hi - 3) / 2
        r.doors.append(Opening(wall=wall, offset=round(offset, 4), width=3))
        design.entrances.append(Entrance(room_id=r.room_id, wall=wall, offset=round(offset, 4), width=3))
        meta["entrance_room"] = r.room_id
    else:
        meta["finishing_failures"].append("NO_VALID_ENTRANCE_WALL")

    # Step 15-19: Windows
    for r in design.rooms:
        if room_kind(r.room_type) in {'hallway', 'staircase'}: continue
        intent = next((i for i in program.rooms if i.id == r.room_id), None)
        if intent and intent.exterior_wall_required:
            meta["rooms_with_required_windows"] += 1
            
        for wall, lo, hi in exterior_segments(r, design.rooms):
            width = min(4, hi - lo)
            offset = lo
            rel_offset = round(offset, 4)
            # check conflict with doors
            conflict = False
            for d in r.doors:
                if d.wall == wall and min(rel_offset + width, d.offset + d.width) > max(rel_offset, d.offset):
                    conflict = True
            if conflict: continue
            
            r.windows.append(Opening(wall=wall, offset=rel_offset, width=width))
            meta["windows_generated"] += 1
            if intent and intent.exterior_wall_required:
                meta["window_requirements_satisfied"] += 1
            break
            
    # Step 21: Final Connectivity Validation
    graph = {r.room_id: set() for r in design.rooms}
    for c in design.connections:
        graph[c.from_room].add(c.to_room)
        graph[c.to_room].add(c.from_room)
        
    if design.entrances:
        seen = set()
        queue = deque([design.entrances[0].room_id])
        while queue:
            node = queue.popleft()
            if node not in seen:
                seen.add(node)
                queue.extend(graph.get(node, set()) - seen)
        
        unreachable = [r.room_id for r in design.rooms if r.room_id not in seen]
        if unreachable:
            meta["unreachable_rooms"] = unreachable
            meta["finishing_failures"].append("ROOM_UNREACHABLE")
            
    meta["finishing_ms"] = int((time.time() - t0) * 1000)
    return design, meta
