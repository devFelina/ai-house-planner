"""Bounded interpretation for common human revision phrases.

Gemini receives the original free text in production. These deterministic
adjustments keep the demo fallback useful without pretending to understand
arbitrary architectural instructions.
"""
from typing import Any, Optional


def apply_supported_revision(preferences: dict[str, Any], prompt: Optional[str]) -> tuple[dict[str, Any], list[str]]:
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


def requests_another_design(prompt: Optional[str]) -> bool:
    if not prompt:
        return False
    text = prompt.lower()
    return any(term in text for term in (
        'another design', 'another layout', 'another floor plan',
        'change topology', 'try another', 'different design', 'different layout',
    ))
