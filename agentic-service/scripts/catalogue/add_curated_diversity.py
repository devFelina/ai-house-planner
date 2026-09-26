from __future__ import annotations

"""Add the small, hand-authored diversity set to the base-plan seed file.

This script is deliberately idempotent.  It replaces only plans whose codes use
the HP-CURATED prefix and leaves the historical catalogue untouched.
"""

import json
import logging
from pathlib import Path

from app.design.quality.architectural_quality import validate_architectural_quality
from app.design.generation.diversity import geometry_fingerprint
from app.design.program.models import Requirements
from app.design.generation.plan_adapter import finish_layout
from app.design.geometry.plot_constraints import PlotConstraints
from app.design.program.room_counts import count_bathrooms
from app.schemas.design_result import DesignResult, RoomLayout
from app.validation.geometry_validator import validate_geometry

LOG = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = ROOT / "HousePlanner.API/Data/Seed/pre-designed-plans.json"
PREFIX = "HP-CURATED-"


def room(room_id, room_type, floor, x, y, width, length):
    return (room_id, room_type, floor, x, y, width, length)


ONE_BATH = {
    "COMPACT_RECTANGLE": [
        room("living", "living_room", 1, 0, 0, 16, 12), room("kitchen", "kitchen", 1, 16, 0, 10, 12),
        room("bath", "bathroom", 1, 26, 0, 6, 12), room("h1", "hallway", 1, 0, 12, 12, 4),
        room("h2", "hallway", 1, 12, 12, 10, 4), room("h3", "hallway", 1, 22, 12, 10, 4),
        room("b1", "bedroom_1", 1, 0, 16, 10, 14), room("b2", "bedroom_2", 1, 10, 16, 10, 14),
        room("b3", "bedroom_3", 1, 20, 16, 12, 14),
    ],
    "L_SHAPE": [
        room("living", "living_room", 1, 0, 0, 14, 12), room("kitchen", "kitchen", 1, 14, 0, 10, 12),
        room("bath", "bathroom", 1, 24, 0, 6, 12), room("dining", "dining", 1, 30, 0, 10, 16),
        room("h1", "hallway", 1, 0, 12, 10, 4), room("h2", "hallway", 1, 10, 12, 10, 4),
        room("h3", "hallway", 1, 20, 12, 10, 4), room("b1", "bedroom_1", 1, 0, 16, 10, 18),
        room("b2", "bedroom_2", 1, 10, 16, 10, 18), room("b3", "bedroom_3", 1, 20, 16, 10, 18),
    ],
    "CENTRAL_CORE": [
        room("bath", "bathroom", 1, 0, 0, 6, 12), room("living", "living_room", 1, 6, 0, 16, 12),
        room("kitchen", "kitchen", 1, 22, 0, 13, 12), room("h1", "hallway", 1, 0, 12, 12, 4),
        room("h2", "hallway", 1, 12, 12, 13, 4), room("dining", "dining", 1, 25, 12, 10, 8),
        room("b1", "bedroom_1", 1, 0, 16, 12, 14), room("b2", "bedroom_2", 1, 12, 16, 9, 14),
        room("h3", "hallway", 1, 21, 16, 4, 14), room("b3", "bedroom_3", 1, 25, 20, 10, 10),
    ],
    "SPLIT_ZONE": [
        room("living", "living_room", 1, 0, 0, 17, 10), room("h1", "hallway", 1, 17, 0, 4, 10),
        room("bath", "bathroom", 1, 21, 0, 7, 10), room("b1", "bedroom_1", 1, 28, 0, 11, 10),
        room("kitchen", "kitchen", 1, 0, 10, 12, 10), room("family", "family_lounge", 1, 12, 10, 18, 10),
        room("lobby", "hallway", 1, 30, 10, 9, 10), room("dining", "dining", 1, 0, 20, 17, 10),
        room("h3", "hallway", 1, 17, 20, 4, 10), room("b2", "bedroom_2", 1, 21, 20, 9, 10),
        room("b3", "bedroom_3", 1, 30, 20, 9, 10),
    ],
}

TWO_BATH = {
    "COMPACT_RECTANGLE": [
        room("living", "living_room", 1, 0, 0, 16, 12), room("kitchen", "kitchen", 1, 16, 0, 10, 12),
        room("ba", "bathroom", 1, 26, 0, 6, 12), room("bb", "bathroom", 1, 32, 0, 6, 12),
        room("h1", "hallway", 1, 0, 12, 12, 4), room("h2", "hallway", 1, 12, 12, 13, 4),
        room("h3", "hallway", 1, 25, 12, 13, 4), room("b1", "bedroom_1", 1, 0, 16, 12, 14),
        room("b2", "bedroom_2", 1, 12, 16, 12, 14), room("b3", "bedroom_3", 1, 24, 16, 14, 14),
    ],
    "CENTRAL_CORE": [
        room("ba", "bathroom", 1, 0, 0, 6, 12), room("bb", "bathroom", 1, 6, 0, 6, 12),
        room("living", "living_room", 1, 12, 0, 13, 12), room("kitchen", "kitchen", 1, 25, 0, 10, 12),
        room("h1", "hallway", 1, 0, 12, 12, 4), room("h2", "hallway", 1, 12, 12, 13, 4),
        room("dining", "dining", 1, 25, 12, 10, 8), room("b1", "bedroom_1", 1, 0, 16, 12, 14),
        room("b2", "bedroom_2", 1, 12, 16, 9, 14), room("h3", "hallway", 1, 21, 16, 4, 14),
        room("b3", "bedroom_3", 1, 25, 20, 10, 10),
    ],
    "SPLIT_ZONE": [
        room("living", "living_room", 1, 0, 0, 17, 10), room("h1", "hallway", 1, 17, 0, 4, 10),
        room("ba", "bathroom", 1, 21, 0, 7, 5), room("bb", "bathroom", 1, 21, 5, 7, 5),
        room("b1", "bedroom_1", 1, 28, 0, 11, 10), room("kitchen", "kitchen", 1, 0, 10, 12, 10),
        room("family", "family_lounge", 1, 12, 10, 18, 10), room("lobby", "hallway", 1, 30, 10, 9, 10),
        room("dining", "dining", 1, 0, 20, 17, 10), room("h3", "hallway", 1, 17, 20, 4, 10),
        room("b2", "bedroom_2", 1, 21, 20, 9, 10), room("b3", "bedroom_3", 1, 30, 20, 9, 10),
    ],
    "LINEAR": [
        room("living", "living_room", 1, 0, 0, 16, 12), room("kitchen", "kitchen", 1, 16, 0, 12, 12),
        room("ba", "bathroom", 1, 0, 12, 12, 6), room("bb", "bathroom", 1, 0, 18, 12, 6),
        room("h0", "hallway", 1, 12, 12, 4, 12), room("family", "family_lounge", 1, 16, 12, 12, 12),
        room("b1", "bedroom_1", 1, 0, 24, 12, 14), room("h3a", "hallway", 1, 12, 24, 4, 14),
        room("b2", "bedroom_2", 1, 16, 24, 12, 14), room("b3", "bedroom_3", 1, 0, 38, 12, 14),
        room("h3b", "hallway", 1, 12, 38, 4, 14), room("family2", "family_lounge", 1, 16, 38, 12, 14),
    ],
}

TWO_FLOOR_COMPACT = [
    room("living", "living_room", 1, 0, 0, 18, 12), room("kitchen", "kitchen", 1, 18, 0, 8, 12),
    room("bath1", "bathroom", 1, 26, 0, 6, 12), room("utility1", "family_lounge", 1, 32, 0, 8, 12),
    room("dining", "dining", 1, 0, 12, 18, 10), room("h1", "hallway", 1, 18, 12, 14, 4),
    room("hmid", "hallway", 1, 18, 16, 4, 8), room("study0", "home_office", 1, 22, 16, 10, 8),
    room("family1", "family_lounge", 1, 32, 12, 8, 12), room("b1", "bedroom_1", 1, 0, 22, 18, 12),
    room("h2", "hallway", 1, 18, 24, 4, 10), room("st1", "staircase", 1, 22, 24, 6, 10),
    room("study1", "home_office", 1, 28, 24, 12, 10), room("b2", "bedroom_2", 2, 0, 0, 12, 12),
    room("uh1a", "hallway", 2, 12, 0, 4, 12), room("b4", "bedroom_4", 2, 16, 0, 12, 12),
    room("family2", "family_lounge", 2, 28, 0, 10, 12), room("b3", "bedroom_3", 2, 0, 12, 12, 12),
    room("uh1b", "hallway", 2, 12, 12, 4, 12), room("bath2", "bathroom", 2, 16, 12, 6, 12),
    room("family3", "family_lounge", 2, 22, 12, 16, 12), room("study2", "home_office", 2, 0, 24, 12, 10),
    room("uh2", "hallway", 2, 12, 24, 10, 4), room("utility", "utility", 2, 12, 28, 6, 6),
    room("st2", "staircase", 2, 22, 24, 6, 10), room("family4", "family_lounge", 2, 28, 24, 10, 10),
]


def two_floor_variants():
    compact = list(TWO_FLOOR_COMPACT)
    central = []
    for item in compact:
        if item[0] == "b1":
            item = room("family_ground", "family_lounge", *item[2:])
        elif item[0] == "study1":
            item = room("b1", "bedroom_1", *item[2:])
        central.append(item)
    split = []
    for item in compact:
        values = list(item)
        if item[0] in {"utility1", "family1", "study1"}:
            values[5] += 4
        if item[0] in {"family2", "family3"}:
            values[5] += 6
        if item[0] == "family4":
            values[5] += 4
        split.append(tuple(values))
    l_shape = []
    for item in compact:
        if item[0] in {"study1", "family4"}:
            continue
        values = list(item)
        if item[0] in {"utility1", "family1"}:
            values[5] = 12
        if item[0] == "family2":
            values[5] = 16
        if item[0] == "family3":
            values[5] = 22
        l_shape.append(tuple(values))
    return {"COMPACT_RECTANGLE": compact, "CENTRAL_CORE": central,
            "SPLIT_ZONE": split, "L_SHAPE": l_shape}


def build_design(code, family, definitions, floors):
    design = DesignResult(
        floor_count=floors, foundation_type="slab", terrain_type="flat",
        template_id=code, template_family=family,
        rooms=[RoomLayout(room_id=i, room_type=t, floor=f, x=x, y=y, width=w, length=l)
               for i, t, f, x, y, w, l in definitions],
    )
    return finish_layout(design, "south", False)


def curated_designs():
    result = []
    for baths, collection in ((1, ONE_BATH), (2, TWO_BATH)):
        for family, definitions in collection.items():
            code = f"{PREFIX}3B{baths}B-1F-{family}"
            result.append((code, 3, baths, 1, family, build_design(code, family, definitions, 1)))
    for family, definitions in two_floor_variants().items():
        code = f"{PREFIX}4B2B-2F-{family}"
        result.append((code, 4, 2, 2, family, build_design(code, family, definitions, 2)))
    return result


def validate_curated(designs):
    fingerprints = set()
    for code, bedrooms, bathrooms, floors, _family, design in designs:
        if count_bathrooms(design.rooms) != bathrooms:
            LOG.warning("Skipping %s: configured bathroom count does not match rooms", code)
            raise ValueError(f"{code}: bathroom count mismatch")
        plot = PlotConstraints(land_size_perches=50, plot_width_ft=100, plot_length_ft=100,
                               road_side="south", terrain_type="flat")
        geometry = validate_geometry(design.rooms, bedrooms, floors, plot.land_size_perches,
                                     plot=plot, design=design)
        quality = validate_architectural_quality(
            design, Requirements(bedrooms=bedrooms, bathrooms=bathrooms, floors=floors), plot)
        if not geometry.passed:
            raise ValueError(f"{code}: geometry failed: {geometry.failures}")
        if not quality.passed:
            raise ValueError(f"{code}: architectural quality failed: {quality.failures}")
        fingerprint = geometry_fingerprint(design)
        if fingerprint in fingerprints:
            raise ValueError(f"{code}: duplicate curated geometry")
        fingerprints.add(fingerprint)


def seed_entry(code, bedrooms, bathrooms, floors, family, design):
    max_x = max(r.x + r.width for r in design.rooms)
    max_y = max(r.y + r.length for r in design.rooms)
    return {
        "designCode": code, "name": code.replace("HP-CURATED-", "Curated ").replace("_", " "),
        "bedrooms": bedrooms, "bathrooms": bathrooms, "floors": floors,
        "topologyFamily": family, "minimumLandSizePerches": 10, "maximumLandSizePerches": 50,
        "minimumPlotWidthFt": max_x + 10, "minimumPlotLengthFt": max_y + 17,
        "supportedPlotShapes": ["COMPACT", "BALANCED", "NARROW", "LARGE"],
        "supportedTerrains": ["flat"],
        "supportedStyles": ["Modern Minimalist", "Contemporary", "Traditional Sri Lankan"],
        "capabilities": {"open_plan": False, "master_ensuite": False, "separate_dining": True,
                         "home_office": any(r.room_type == "home_office" for r in design.rooms),
                         "balcony": False, "veranda": False, "utility_room": True,
                         "parking": False, "accessibility": floors == 1},
        "architecturalMetrics": {"curated": 1.0},
        "layout": design.model_dump(mode="json", exclude_none=True), "isActive": True,
    }


def main():
    logging.basicConfig(level=logging.INFO)
    designs = curated_designs()
    validate_curated(designs)
    current = json.loads(SEED_PATH.read_text())
    generated_codes = {item[0] for item in designs}
    current = [item for item in current if item.get("designCode") not in generated_codes]
    current.extend(seed_entry(*item) for item in designs)
    SEED_PATH.write_text(json.dumps(current, indent=2) + "\n")
    print(f"Wrote {len(designs)} curated plans; catalogue now has {len(current)} entries.")


if __name__ == "__main__":
    main()
