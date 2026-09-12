"""Topology rules contain no finished room coordinates."""
from dataclasses import asdict, dataclass
from app.design.models import Requirements
from app.design.plot_constraints import PlotConstraints


@dataclass(frozen=True)
class Topology:
    name: str
    min_width: float
    min_length: float
    supported_floors: tuple[int, ...]
    bedroom_range: tuple[int, int]
    terrains: tuple[str, ...]
    zoning: str
    adjacency: tuple[str, ...]


TOPOLOGIES = [
    Topology('LINEAR', 14, 28, (1, 2, 3), (1, 8), ('flat', 'hillside', 'coastal'), 'single bank on a longitudinal circulation spine', ('entrance-circulation-rooms',)),
    Topology('COMPACT_RECTANGLE', 24, 24, (1, 2, 3), (1, 8), ('flat', 'hillside', 'coastal'), 'balanced double bank', ('living-kitchen', 'hall-bedrooms')),
    Topology('L_SHAPE', 32, 30, (1,), (2, 6), ('flat',), 'public garden wing and private return wing', ('living-kitchen', 'hall-bedrooms')),
    Topology('T_SHAPE', 38, 32, (1,), (3, 8), ('flat',), 'public crossbar and private stem', ('living-kitchen', 'hall-bedrooms')),
    Topology('CENTRAL_CORE', 28, 26, (1, 2, 3), (1, 6), ('flat',), 'wide central foyer between banks', ('foyer-rooms',)),
    Topology('SPLIT_ZONE', 26, 26, (1, 2, 3), (2, 8), ('flat',), 'public and private banks separated by circulation', ('living-kitchen', 'hall-bedrooms')),
    Topology('DUPLEX_STACKED', 24, 24, (2, 3), (1, 8), ('flat', 'hillside', 'coastal'), 'stacked stair core and floor-specific zones', ('stairs-hall', 'hall-bedrooms')),
    Topology('HILLSIDE_STEPPED', 24, 26, (1, 2, 3), (1, 6), ('hillside',), 'offset compact banks along contour; conceptual only', ('hall-rooms',)),
    Topology('COASTAL_RAISED_COMPACT', 24, 24, (1, 2, 3), (1, 8), ('coastal',), 'compact raised-compatible banks', ('hall-rooms',)),
]


def eligible_topologies(req: Requirements, plot: PlotConstraints) -> list[Topology]:
    width, length = plot.buildable_width, plot.buildable_length
    def fits(t: Topology) -> bool:
        return ((width >= t.min_width and length >= t.min_length) or
                (length >= t.min_width and width >= t.min_length))
    return [t for t in TOPOLOGIES if fits(t) and req.floors in t.supported_floors
            and t.bedroom_range[0] <= req.bedrooms <= t.bedroom_range[1]
            and plot.terrain_type in t.terrains]


def topology_dict(topology: Topology) -> dict:
    return asdict(topology)
