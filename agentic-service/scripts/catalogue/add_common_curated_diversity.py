from __future__ import annotations

"""Add a focused second set of hand-authored common-configuration plans."""

import json

from app.design.generation.diversity import geometry_fingerprint
from app.schemas.design_result import DesignResult
from scripts.catalogue.add_curated_diversity import (
    SEED_PATH,
    build_design,
    seed_entry,
    two_floor_variants,
    validate_curated,
)

PREFIX = "HP-CURATED-COMMON-"
R = lambda *values: values

TWO_BED_ONE_BATH = {
    "COMPACT_RECTANGLE": [
        R("living", "living_room", 1, 0, 0, 14, 12), R("kitchen", "kitchen", 1, 14, 0, 8, 12),
        R("bath", "bathroom", 1, 22, 0, 6, 12), R("h1", "hallway", 1, 0, 12, 14, 4),
        R("h2", "hallway", 1, 14, 12, 14, 4), R("b1", "bedroom_1", 1, 0, 16, 14, 12),
        R("b2", "bedroom_2", 1, 14, 16, 14, 12),
    ],
    "L_SHAPE": [
        R("living", "living_room", 1, 0, 0, 14, 12), R("kitchen", "kitchen", 1, 14, 0, 8, 12),
        R("bath", "bathroom", 1, 22, 0, 6, 12), R("dining", "dining", 1, 28, 0, 12, 16),
        R("h1", "hallway", 1, 0, 12, 14, 4), R("h2", "hallway", 1, 14, 12, 14, 4),
        R("b1", "bedroom_1", 1, 0, 16, 14, 16), R("b2", "bedroom_2", 1, 14, 16, 14, 16),
    ],
    "SPLIT_ZONE": [
        R("living", "living_room", 1, 0, 0, 17, 10), R("kitchen", "kitchen", 1, 17, 0, 17, 10),
        R("family1", "family_lounge", 1, 0, 10, 8, 10), R("bath", "bathroom", 1, 8, 10, 6, 10),
        R("ha", "hallway", 1, 14, 10, 6, 10), R("family2", "family_lounge", 1, 20, 10, 14, 10),
        R("b1", "bedroom_1", 1, 0, 20, 14, 14), R("hb", "hallway", 1, 14, 20, 6, 14),
        R("b2", "bedroom_2", 1, 20, 20, 14, 14),
    ],
}

TWO_BED_TWO_BATH = {
    "COMPACT_RECTANGLE": [
        R("living", "living_room", 1, 0, 0, 14, 12), R("kitchen", "kitchen", 1, 14, 0, 10, 12),
        R("ba", "bathroom", 1, 24, 0, 6, 12), R("bb", "bathroom", 1, 30, 0, 6, 12),
        R("h1", "hallway", 1, 0, 12, 18, 4), R("h2", "hallway", 1, 18, 12, 18, 4),
        R("b1", "bedroom_1", 1, 0, 16, 18, 12), R("b2", "bedroom_2", 1, 18, 16, 18, 12),
    ],
    "L_SHAPE": [
        R("living", "living_room", 1, 0, 0, 14, 12), R("kitchen", "kitchen", 1, 14, 0, 10, 12),
        R("ba", "bathroom", 1, 24, 0, 6, 12), R("bb", "bathroom", 1, 30, 0, 6, 12),
        R("family", "family_lounge", 1, 36, 0, 12, 16), R("h1", "hallway", 1, 0, 12, 18, 4),
        R("h2", "hallway", 1, 18, 12, 18, 4), R("b1", "bedroom_1", 1, 0, 16, 18, 16),
        R("b2", "bedroom_2", 1, 18, 16, 18, 16),
    ],
    "CENTRAL_CORE": [
        R("ba", "bathroom", 1, 0, 0, 6, 12), R("bb", "bathroom", 1, 6, 0, 6, 12),
        R("living", "living_room", 1, 12, 0, 12, 12), R("kitchen", "kitchen", 1, 24, 0, 10, 12),
        R("h1", "hallway", 1, 0, 12, 12, 4), R("core", "hallway", 1, 12, 12, 12, 4),
        R("dining", "dining", 1, 24, 12, 10, 8), R("b1", "bedroom_1", 1, 0, 16, 12, 14),
        R("b2", "bedroom_2", 1, 12, 16, 12, 14),
    ],
}

TWO_FLOOR_SPLIT = [
    R("living", "living_room", 1, 0, 0, 10, 12), R("kitchen", "kitchen", 1, 10, 0, 10, 12),
    R("hall1", "hallway", 1, 20, 0, 6, 12), R("bath1", "bathroom", 1, 26, 0, 6, 6),
    R("bath2", "bathroom", 1, 26, 6, 6, 6), R("family0", "family_lounge", 1, 32, 0, 12, 12),
    R("dining", "dining", 1, 0, 12, 18, 10), R("bridge", "family_lounge", 1, 18, 12, 8, 10),
    R("family1", "family_lounge", 1, 26, 12, 18, 10), R("family2", "family_lounge", 1, 0, 22, 20, 12),
    R("st1", "staircase", 1, 20, 22, 6, 12), R("b1", "bedroom_1", 1, 26, 22, 18, 12),
    R("b2", "bedroom_2", 2, 0, 0, 20, 11), R("hall2a", "hallway", 2, 20, 0, 6, 11),
    R("b4", "bedroom_4", 2, 26, 0, 18, 11), R("b3", "bedroom_3", 2, 0, 11, 20, 11),
    R("hall2b", "hallway", 2, 20, 11, 6, 11), R("family3", "family_lounge", 2, 26, 11, 18, 11),
    R("family4", "family_lounge", 2, 0, 22, 20, 12), R("st2", "staircase", 2, 20, 22, 6, 12),
    R("bath3", "bathroom", 2, 26, 22, 6, 12), R("family5", "family_lounge", 2, 32, 22, 12, 12),
]


def replace_types(definitions, changes):
    output = []
    for definition in definitions:
        values = list(definition)
        if values[0] in changes:
            values[1] = changes[values[0]]
        output.append(tuple(values))
    return output


def central_wide_five_bed(definitions):
    output = []
    for definition in definitions:
        values = list(definition)
        if values[0] in {"utility1", "family1", "b1"}:
            values[5] += 8
        if values[0] in {"family2", "family3"}:
            values[5] += 10
        if values[0] == "family4":
            values[5] += 8
        output.append(tuple(values))
    return replace_types(output, {"utility": "bathroom", "family_ground": "bedroom_5"})


def curated_designs():
    designs = []
    for bathrooms, collection in ((1, TWO_BED_ONE_BATH), (2, TWO_BED_TWO_BATH)):
        for family, definitions in collection.items():
            code = f"{PREFIX}2B{bathrooms}B-1F-{family}"
            designs.append((code, 2, bathrooms, 1, family,
                            build_design(code, family, definitions, 1)))

    variants = two_floor_variants()
    for family in ("COMPACT_RECTANGLE", "L_SHAPE", "SPLIT_ZONE"):
        code = f"{PREFIX}4B3B-2F-{family}"
        definitions = (TWO_FLOOR_SPLIT if family == "SPLIT_ZONE" else
                       replace_types(variants[family], {"utility": "bathroom"}))
        designs.append((code, 4, 3, 2, family, build_design(code, family, definitions, 2)))

    five_bed = {
        "COMPACT_RECTANGLE": replace_types(
            variants["COMPACT_RECTANGLE"], {"utility": "bathroom", "study1": "bedroom_5"}),
        "SPLIT_ZONE": replace_types(
            TWO_FLOOR_SPLIT, {"family2": "bedroom_5"}),
        "CENTRAL_CORE": central_wide_five_bed(variants["CENTRAL_CORE"]),
    }
    for family, definitions in five_bed.items():
        code = f"{PREFIX}5B3B-2F-{family}"
        designs.append((code, 5, 3, 2, family, build_design(code, family, definitions, 2)))
    return designs


def validate_against_catalogue(designs, current):
    existing = {
        geometry_fingerprint(DesignResult.model_validate(item["layout"]))
        for item in current if not item.get("designCode", "").startswith(PREFIX)
        and isinstance(item.get("layout"), dict)
    }
    for code, *_rest, design in designs:
        fingerprint = geometry_fingerprint(design)
        if fingerprint in existing:
            raise ValueError(f"{code}: geometry duplicates an existing catalogue plan")
        existing.add(fingerprint)


def main():
    designs = curated_designs()
    validate_curated(designs)
    current = json.loads(SEED_PATH.read_text())
    validate_against_catalogue(designs, current)
    generated_codes = {item[0] for item in designs}
    current = [item for item in current if item.get("designCode") not in generated_codes]
    current.extend(seed_entry(*item) for item in designs)
    SEED_PATH.write_text(json.dumps(current, indent=2) + "\n")
    print(f"Wrote {len(designs)} common curated plans; catalogue now has {len(current)} entries.")


if __name__ == "__main__":
    main()
