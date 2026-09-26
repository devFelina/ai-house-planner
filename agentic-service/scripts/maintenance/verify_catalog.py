import json


def room_overlaps(a, b):
    overlap_x = max(0, min(a['x'] + a['width'], b['x'] + b['width']) - max(a['x'], b['x']))
    overlap_y = max(0, min(a['y'] + a.get('length', 0), b['y'] + b.get('length', 0)) - max(a['y'], b['y']))
    return overlap_x > 0 and overlap_y > 0

with open('../HousePlanner.API/Data/Seed/pre-designed-plans.json') as f:
    plans = json.load(f)

print(f"Total plans: {len(plans)}")

design_codes = set()
duplicates = 0
stair_missing = 0
stair_misaligned = 0
invalid_bedroom_counts = 0
invalid_bathroom_counts = 0
invalid_floor_counts = 0
hallway_issues = 0
overlaps = 0
fingerprints = set()
duplicate_fingerprints = 0

for p in plans:
    code = p['designCode']
    if code in design_codes:
        duplicates += 1
    design_codes.add(code)

    beds = p['bedrooms']
    baths = p['bathrooms']
    floors = p['floors']
    rooms = p['layout']['rooms']

    # Check bedroom counts
    bed_count = sum(1 for r in rooms if 'bedroom' in r['room_type'])
    if bed_count != beds:
        invalid_bedroom_counts += 1

    bath_count = sum(1 for r in rooms if 'bathroom' in r['room_type'])
    if bath_count < baths:
        invalid_bathroom_counts += 1

    # Check floor counts
    floor_count = max([r['floor'] for r in rooms]) if rooms else 0
    if floor_count != floors:
        invalid_floor_counts += 1

    # Check missing stairs for multi-floor
    if floors > 1:
        staircases = [r for r in rooms if r['room_type'] == 'staircase']
        if len(staircases) < floors:
            stair_missing += 1
        else:
            first_stair = staircases[0]
            for s in staircases[1:]:
                if s['x'] != first_stair['x'] or s['y'] != first_stair['y'] or s['width'] != first_stair['width'] or s['length'] != first_stair['length']:
                    stair_misaligned += 1

    # Check hallway widths (min 3.5)
    for r in rooms:
        if r['room_type'] == 'hallway' and r['width'] < 3.5:
            hallway_issues += 1

    # Check overlaps
    for i, a in enumerate(rooms):
        for b in rooms[i+1:]:
            if a['floor'] == b['floor'] and room_overlaps(a, b):
                overlaps += 1

    # check fingerprints
    fp = "-".join(f"{r['room_type']}:{r['x']}:{r['y']}:{r['width']}:{r.get('length', 0)}" for r in sorted(rooms, key=lambda x: x['room_id']))
    if fp in fingerprints:
        duplicate_fingerprints += 1
    fingerprints.add(fp)

print(f"Unique designCodes: {len(design_codes)}")
print(f"Duplicate designCodes: {duplicates}")
print(f"Unique geometry fingerprints: {len(fingerprints)}")
print(f"Duplicate fingerprints: {duplicate_fingerprints}")
print(f"Invalid bedroom counts: {invalid_bedroom_counts}")
print(f"Invalid bathroom counts: {invalid_bathroom_counts}")
print(f"Invalid floor counts: {invalid_floor_counts}")
print(f"Missing stairs: {stair_missing}")
print(f"Misaligned stairs: {stair_misaligned}")
print(f"Hallway width violations: {hallway_issues}")
print(f"Room overlaps: {overlaps}")
