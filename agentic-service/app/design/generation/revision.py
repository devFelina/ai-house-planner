"""Bounded interpretation for common human revision phrases.

Gemini receives the original free text in production. These deterministic
adjustments keep the demo fallback useful without pretending to understand
arbitrary architectural instructions.
"""
from typing import Any

from app.design.program.models import Requirements
from app.design.program.room_counts import count_bathrooms


def preserve_revision_preferences(preferences: dict, previous_design: dict | None) -> dict:
    """Explicit request values override saved requirements, then room counts."""
    previous = previous_design or {}
    summary = previous.get('candidate_summary') or {}
    normalized = summary.get('normalized_input') or {}
    aliases = {'architectural_style': 'style', 'master_ensuite': 'attached_bathroom',
               'separate_dining': 'dining_required', 'parking_required': 'parking'}
    preserved = {aliases.get(key, key): value for key, value in normalized.items()
                 if aliases.get(key, key) in Requirements.model_fields and value is not None}
    preserved.update({aliases.get(key, key): value for key, value in preferences.items() if value is not None})
    if preserved.get('bathrooms') is None:
        bathrooms = count_bathrooms(previous.get('rooms') or [])
        if bathrooms < 1:
            raise ValueError('Revision requires a bathroom count from the request or previous design.')
        preserved['bathrooms'] = bathrooms
    return preserved


def apply_supported_revision(preferences: dict[str, Any], prompt: str | None) -> tuple[dict[str, Any], list[str]]:
    updated = dict(preferences)
    if not prompt:
        return updated, []
    text = prompt.lower().strip()
    applied: list[str] = []
    if any(term in text for term in ('open plan', 'open-plan')):
        updated['open_plan'] = True
        applied.append('open_plan')
    if 'garden' in text:
        updated['garden_priority'] = True
        applied.append('garden_priority')
    if any(term in text for term in ('more compact', 'reduce footprint', 'smaller footprint')):
        updated['compact_priority'] = True
        applied.append('compact_priority')
    if any(term in text for term in ('separate bedrooms', 'more privacy', 'bedrooms from living')):
        updated['privacy_priority'] = True
        applied.append('privacy_priority')
    if any(term in text for term in ('larger living', 'living room bigger', 'bigger living')):
        updated['living_area_scale'] = 1.2
        applied.append('living_area_scale')
    if any(term in text for term in ('larger kitchen', 'kitchen bigger', 'bigger kitchen')):
        updated['kitchen_area_scale'] = 1.2
        applied.append('kitchen_area_scale')
    return updated, applied


def requests_another_design(prompt: str | None) -> bool:
    if not prompt:
        return False
    text = prompt.lower()
    return any(term in text for term in (
        'generate another', 'another design', 'another layout', 'another floor plan',
        'change topology', 'try another', 'different design', 'different layout',
    ))
