"""Single source of conceptual architectural limits (not building regulations)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class QualityConfig:
    circulation_excellent: float = .08
    circulation_acceptable: float = .12
    circulation_reject: float = .15
    hallway_preferred_ft: float = 20
    hallway_max_ft: float = 28
    hallway_max_aspect: float = 6.5
    hallway_max_footprint_fraction: float = .75
    dead_end_max_ft: float = 18
    public_travel_max_ft: float = 30
    bedroom_travel_max_ft: float = 44
    bathroom_travel_max_ft: float = 32
    entrance_public_max_ft: float = 14
    wet_core_max_ft: float = 30
    minimum_compactness: float = .68
    minimum_score: float = 72
    hard_failure_score_cap: float = 59

QUALITY = QualityConfig()
WEIGHTS = {"circulation_efficiency": .20, "compactness": .10, "public_zone_quality": .14,
               "private_zone_quality": .12, "wet_core_quality": .08, "entrance_quality": .10,
               "privacy": .08, "topology_fidelity": .10, "preference_match": .08}
