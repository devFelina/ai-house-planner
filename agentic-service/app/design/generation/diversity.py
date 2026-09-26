import hashlib
import json
import random
from decimal import Decimal
from uuid import UUID, uuid5

DESIGN_NAMESPACE = UUID('b1a10b30-c1f4-4e11-95a0-b10dbd583b01')


def stable_seed(payload: dict) -> int:
    return int(hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12], 16)


def candidate_rng(seed: int, family: str, index: int) -> random.Random:
    return random.Random(stable_seed({'seed': seed, 'family': family, 'index': index}))


def stable_id(key: str) -> str:
    return str(uuid5(DESIGN_NAMESPACE, key))


def geometry_fingerprint(layout) -> str:
    """Hash geometry and access topology, independent of IDs and metadata.

    Coordinates are not rounded or transformed. Connections are undirected;
    their kind and multiplicity, and entrance placement, remain significant.
    """
    def number(value):
        value = Decimal(str(value))
        if not value.is_finite():
            raise ValueError('Geometry coordinates must be finite.')
        return format(value.normalize(), 'f') if value else '0'

    rooms = {
        r.room_id: (r.room_type, r.floor, number(r.x), number(r.y),
                    number(r.width), number(r.length))
        for r in layout.rooms
    }
    if len(rooms) != len(layout.rooms):
        raise ValueError('Geometry fingerprint requires unique room IDs.')
    normalized = {
        'rooms': sorted(rooms.values()),
        'connections': sorted(
            (tuple(sorted((rooms[c.from_room], rooms[c.to_room]))), c.kind)
            for c in layout.connections
        ),
        'entrances': sorted(
            (rooms[e.room_id], e.wall, number(e.offset), number(e.width))
            for e in layout.entrances
        ),
    }
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
