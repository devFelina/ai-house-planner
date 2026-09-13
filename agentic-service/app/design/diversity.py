import hashlib
import json
import random
from uuid import UUID, uuid5

DESIGN_NAMESPACE = UUID('b1a10b30-c1f4-4e11-95a0-b10dbd583b01')


def stable_seed(payload: dict) -> int:
    return int(hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12], 16)


def candidate_rng(seed: int, family: str, index: int) -> random.Random:
    return random.Random(stable_seed({'seed': seed, 'family': family, 'index': index}))


def stable_id(key: str) -> str:
    return str(uuid5(DESIGN_NAMESPACE, key))


def geometry_fingerprint(layout) -> str:
    normalized = sorted(
        (r.room_type, r.floor, round(r.x, 3), round(r.y, 3),
         round(r.width, 3), round(r.length, 3))
        for r in layout.rooms
    )
    return hashlib.sha256(
        json.dumps(normalized, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
