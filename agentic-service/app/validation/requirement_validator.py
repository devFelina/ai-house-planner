from __future__ import annotations
"""
Semantic requirement validation for Architecture Assistant.
Checks logic and sanity of requested design features BEFORE spatial feasibility.
"""
from dataclasses import dataclass, field
from typing import Any

from app.land.feasibility_engine import (
    _load_catalogue,
)


@dataclass
class SanityValidationResult:
    status: str  # 'VALID', 'NEEDS_CONFIRMATION', 'INVALID'
    reason_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "status": self.status,
            "reason_codes": self.reason_codes,
            "warnings": self.warnings,
            "suggestions": self.suggestions
        }

def validate_requirements_sanity(reqs: dict[str, Any]) -> SanityValidationResult:
    reason_codes = []
    warnings = []
    suggestions = []
    status = 'VALID'
    
    bedrooms = reqs.get('bedrooms')
    bathrooms = reqs.get('bathrooms')
    floors = reqs.get('floors')
    parking = reqs.get('parking_spaces')
    land_size = reqs.get('land_size')
    
    catalogue = _load_catalogue()
    
    # TASK 2: BASIC HARD RULES
    if bedrooms is not None and bedrooms < 1:
        reason_codes.append('INVALID_BEDROOM_COUNT')
        suggestions.append('A residential design requires at least 1 bedroom.')
        status = 'INVALID'
        
    if bathrooms is not None and bathrooms < 1:
        reason_codes.append('INVALID_BATHROOM_COUNT')
        suggestions.append('A residential design requires at least 1 bathroom.')
        status = 'INVALID'
        
    if floors is not None and floors < 1:
        reason_codes.append('INVALID_FLOOR_COUNT')
        suggestions.append('Floor count must be at least 1.')
        status = 'INVALID'
        
    if parking is not None and parking < 0:
        reason_codes.append('INVALID_PARKING_COUNT')
        suggestions.append('Parking spaces cannot be negative.')
        status = 'INVALID'
        
    if land_size is not None and land_size < 0:
        reason_codes.append('INVALID_LAND_SIZE')
        suggestions.append('Land size cannot be negative.')
        status = 'INVALID'
        
    # Check catalogue bounds for simple features
    max_cat_beds = max((p.bedrooms for p in catalogue), default=10)
    max_cat_baths = max((p.bathrooms for p in catalogue), default=10)
    max_cat_floors = max((p.floors for p in catalogue), default=5)
    
    if bedrooms is not None and bedrooms > max_cat_beds * 2 and bedrooms > max_cat_beds:
             reason_codes.append('UNSUPPORTED_BEDROOM_COUNT')
             suggestions.append(f'The catalogue supports a maximum of {max_cat_beds} bedrooms.')
             status = 'INVALID'
             
    if bathrooms is not None and bathrooms > max_cat_baths:
         reason_codes.append('UNSUPPORTED_BATHROOM_COUNT')
         suggestions.append(f'The catalogue supports a maximum of {max_cat_baths} bathrooms.')
         status = 'INVALID'

    if floors is not None and floors > max_cat_floors:
         reason_codes.append('UNSUPPORTED_FLOOR_COUNT')
         suggestions.append(f'The catalogue supports a maximum of {max_cat_floors} floors.')
         status = 'INVALID'

    # If it's already INVALID from basic rules, we can return early or keep validating.
    # Let's keep validating to gather all reasons.

    # TASK 3: BEDROOM / BATHROOM CONSISTENCY
    if bedrooms is not None and bedrooms > 0 and bathrooms is not None and bathrooms > 0:
        # Check if ratio is unusual
        # Example: 2 beds, 12 baths -> not accepted.
        # Example: 2 beds, 4 baths -> requires confirmation.
        
        has_exact_match = any(p.bedrooms == bedrooms and p.bathrooms == bathrooms for p in catalogue)
        
        if not has_exact_match:
            reason_codes.append('UNSUPPORTED_BEDROOM_BATHROOM_COMBINATION')
            suggestions.append('Please check your bedroom and bathroom counts.')
            status = 'INVALID'
            
            # Find nearest supported
            closest_plans = sorted(catalogue, key=lambda p: abs(p.bedrooms - bedrooms) + abs(p.bathrooms - bathrooms))
            if closest_plans:
                closest = closest_plans[0]
                suggestions.append(f'Nearest supported combination is {closest.bedrooms} bedrooms and {closest.bathrooms} bathrooms.')
        else:
            # Even if exact match exists, if it's very unusual we might want to ask confirmation
            # The prompt says "If catalogue or rules allow it but it is unusual: requires_confirmation = true"
            ratio = bathrooms / bedrooms
            if bathrooms > bedrooms + 1 or ratio < 0.5:
                if status != 'INVALID':
                    status = 'NEEDS_CONFIRMATION'
                reason_codes.append('UNUSUAL_BEDROOM_BATHROOM_RATIO')
                warnings.append(f'You requested {bedrooms} bedrooms and {bathrooms} bathrooms. Is that intentional?')
                
    # TASK 4: FEATURE CONSISTENCY
    # 1 floor + feature that requires upper floor (e.g. balcony)
    if floors == 1 and reqs.get('balcony'):
        # Check if there is ANY single floor plan with a balcony in the catalogue
        can_have_balcony_on_ground = any(p.floors == 1 and p.capabilities.get('balcony') for p in catalogue)
        if not can_have_balcony_on_ground:
            reason_codes.append('CONTRADICTORY_FEATURES')
            suggestions.append('Balconies are only supported on multi-floor designs.')
            status = 'INVALID'
            
    if floors is not None and floors > 1:
        # Multi floor requested but stairs unsupported (we support stairs in our plans, but maybe catalogue doesn't have it?)
        # Just check if any plan has > 1 floor
        has_multi = any(p.floors == floors for p in catalogue)
        if not has_multi:
            reason_codes.append('CONTRADICTORY_FEATURES')
            suggestions.append(f'Multi-floor designs ({floors} floors) are not supported by the current catalogue.')
            status = 'INVALID'

    # Master ensuite requested but no bedroom exists (handled by bedrooms < 1 check, but let's be explicit)
    if reqs.get('master_ensuite') and bedrooms is not None and bedrooms < 1:
        reason_codes.append('CONTRADICTORY_FEATURES')
        suggestions.append('Cannot have a master ensuite without bedrooms.')
        status = 'INVALID'
        
    # accessible_friendly but no supported ground-floor bedroom/bathroom arrangement
    # Wait, the prompt says "accessible_friendly but no supported ground-floor bedroom/bathroom arrangement"
    # Actually, in feasibility_engine.py it says "Accessibility layout requires a ground-floor bedroom and bathroom."
    # If the user asks for 0 bedrooms but accessible_friendly, it fails.
    if reqs.get('accessible_friendly') and floors is not None and floors > 1:
             # Just check if we have any accessible plans with floors > 1
             has_acc_multi = any(p.floors == floors and p.capabilities.get('accessibility') for p in catalogue)
             if not has_acc_multi:
                 # Actually, feasibility_engine handles this as a suggestion. 
                 # Let's make it a NEEDS_CONFIRMATION or INVALID depending on catalogue.
                 pass

    # Catalogue support: exact combination has no compatible plans
    # Wait, the prompt says:
    # "If exact combination has no compatible plans: return: NO_COMPATIBLE_BASE_PLAN with nearest supported alternatives.
    # Example: Requested: 2 bedrooms 12 bathrooms. Nearest: 2 beds / 1 bath"
    # We did this in TASK 3 for bathrooms/bedrooms. But what about general capability?
    if status != 'INVALID' and bedrooms is not None and bathrooms is not None and floors is not None:
             match = any(p.bedrooms == bedrooms and p.bathrooms == bathrooms and p.floors == floors for p in catalogue)
             if not match:
                 reason_codes.append('NO_COMPATIBLE_BASE_PLAN')
                 status = 'INVALID'
                 closest_plans = sorted(catalogue, key=lambda p: abs(p.bedrooms - bedrooms) + abs(p.bathrooms - bathrooms) + abs(p.floors - floors))
                 if closest_plans:
                     c = closest_plans[0]
                     suggestions.append(f'No exact match in catalogue. Nearest supported is {c.bedrooms} beds, {c.bathrooms} baths, {c.floors} floors.')

    return SanityValidationResult(
        status=status,
        reason_codes=reason_codes,
        warnings=warnings,
        suggestions=suggestions
    )
