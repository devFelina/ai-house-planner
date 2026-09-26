import json


def room_overlaps(a, b):
    # A bit of a simplified overlap check
    overlap_x = max(0, min(a['x'] + a['width'], b['x'] + b['width']) - max(a['x'], b['x']))
    overlap_y = max(0, min(a['y'] + a.get('length', 0), b['y'] + b.get('length', 0)) - max(a['y'], b['y']))
    return overlap_x > 0 and overlap_y > 0

with open('../HousePlanner.API/Data/Seed/pre-designed-plans.json') as f:
    plans = json.load(f)

for p in plans:
    beds = p['bedrooms']
    floors = p['floors']
    rooms = p['layout']['rooms']

    bed_count = sum(1 for r in rooms if 'bedroom' in r['room_type'])
    floor_count = max([r['floor'] for r in rooms]) if rooms else 0

    if bed_count != beds or floor_count != floors:
        print(f"Invalid count in {p['designCode']}: target beds={beds}, actual={bed_count}. target floors={floors}, actual={floor_count}")
        break

for p in plans:
    rooms = p['layout']['rooms']
    overlap_found = False
    for i, a in enumerate(rooms):
        for b in rooms[i+1:]:
            if a['floor'] == b['floor'] and room_overlaps(a, b):
                    print(f"Overlap in {p['designCode']}: {a['room_id']} and {b['room_id']} overlap!")
                    print(f"  {a['room_id']}: x={a['x']}, y={a['y']}, w={a['width']}, l={a.get('length')}")
                    print(f"  {b['room_id']}: x={b['x']}, y={b['y']}, w={b['width']}, l={b.get('length')}")
                    overlap_found = True
                    break
        if overlap_found:
            break
    if overlap_found:
        break
