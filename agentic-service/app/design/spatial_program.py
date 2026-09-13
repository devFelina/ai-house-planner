from app.design.models import Requirements, RoomSpec, SpatialProgram
from app.design.room_rules import rule_for


def build_program(req: Requirements) -> SpatialProgram:
    rooms: list[RoomSpec] = []
    def add(key: str, floor: int, zone: str, exterior: bool = False) -> None:
        rule = rule_for(key)
        target = rule.target_area
        if key == 'living_room':
            target *= req.living_area_scale
        if key == 'kitchen':
            target *= req.kitchen_area_scale
        if key == 'living_room' and req.open_plan:
            target += 50
        if key == 'bedroom_1' and req.master_bedroom:
            target += 40
        if key.startswith('bedroom') and req.space_priority == 'larger_bedrooms':
            target *= 1.2
        if key == 'living_room' and req.space_priority == 'spacious_living':
            target *= 1.2
        rooms.append(RoomSpec(id=key, room_type=key, floor=floor, zone=zone,
                              min_width=rule.min_width, min_length=rule.min_length,
                              target_area=target, requires_exterior_wall=exterior))
    add('living_room', 1, 'public', True)
    if req.dining_required or req.open_plan:
        add('dining', 1, 'public', True)
    add('kitchen', 1, 'service')
    for i in range(req.bedrooms):
        floor = 1 if req.floors == 1 else 2 + i % (req.floors - 1)
        if req.accessibility and i == 0:
            floor = 1
        add(f'bedroom_{i+1}', floor, 'private', True)
    for i in range(req.bathrooms):
        floor = 1 if i == 0 else min(req.floors, 2 + (i-1) % max(1, req.floors-1))
        add(f'bathroom_{i+1}', floor, 'service')
    if req.attached_bathroom:
        master = next(r for r in rooms if r.id == 'bedroom_1')
        add('bathroom_attached', master.floor, 'service')
    if req.home_office:
        add('home_office', 1, 'private', True)
    if req.veranda:
        add('veranda', 1, 'public', True)
    if req.utility_room:
        add('utility', 1, 'service', True)
    if req.balcony and req.floors > 1:
        add('balcony', req.floors, 'public', True)
    for floor in range(2, req.floors+1):
        if not any(r.floor == floor and r.zone == 'private' for r in rooms):
            add(f'family_lounge_{floor}', floor, 'private', True)
    adjacency = [('living_room', 'kitchen', 'preferred')]
    if req.dining_required or req.open_plan:
        adjacency = [('living_room', 'dining', 'preferred'), ('dining', 'kitchen', 'required')]
    adjacency += [(r.id, 'bathroom_1', 'preferred') for r in rooms if r.room_type.startswith('bedroom')]
    if req.attached_bathroom:
        adjacency.append(('bedroom_1', 'bathroom_attached', 'required'))
    for bathroom in [r for r in rooms if r.room_type.startswith('bathroom')]:
        adjacency.append(('kitchen', bathroom.id, 'preferred'))
        adjacency.append(('dining', bathroom.id, 'discouraged'))
    for bedroom in [r for r in rooms if r.room_type.startswith('bedroom')]:
        adjacency.append(('kitchen', bedroom.id, 'discouraged'))
    # This graph expresses relationships, not a demand for a dedicated hallway
    # to every room. Public rooms may provide circulation to a private lobby.
    access = [('entrance', 'living_room'), ('living_room', 'public_circulation')]
    access += [('private_circulation', r.id) for r in rooms
               if r.zone == 'private' or r.room_type.startswith('bathroom')]
    notes = []
    if req.balcony and req.floors == 1:
        notes.append('Balcony requires an upper floor; not included in this single-floor program.')
    if req.parking:
        notes.append('An 18 ft front strip is reserved for conceptual parking/access outside the building.')
    if req.accessibility and req.floors > 1:
        notes.append('Ground-floor bedroom and wider circulation provided; upper floors remain stair-accessed.')
    if req.circulation_preference == 'space_efficient':
        notes.append('Prefer short shared circulation and a compact private lobby over a full-length hallway.')
    return SpatialProgram(rooms=rooms, adjacency_preferences=adjacency,
                          separation_preferences=[('living_room', 'bedroom_1')],
                          access_graph=access, notes=notes)
