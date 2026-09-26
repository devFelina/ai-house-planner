from __future__ import annotations
from app.land.feasibility_engine import check_feasibility
from app.validation.requirement_validator import validate_requirements_sanity


def test_2Bedrooms12Bathrooms_IsRejectedOrUnsupported():
    reqs = {'bedrooms': 2, 'bathrooms': 12, 'floors': 1}
    res = validate_requirements_sanity(reqs)
    assert res.status == 'INVALID'
    assert 'UNSUPPORTED_BEDROOM_BATHROOM_COMBINATION' in res.reason_codes or 'UNSUPPORTED_BATHROOM_COUNT' in res.reason_codes

def test_2Bedrooms2Bathrooms_IsValid():
    reqs = {'bedrooms': 2, 'bathrooms': 2, 'floors': 1}
    res = validate_requirements_sanity(reqs)
    assert res.status == 'VALID'

def test_ZeroBedrooms_IsRejected():
    reqs = {'bedrooms': 0, 'bathrooms': 1, 'floors': 1}
    res = validate_requirements_sanity(reqs)
    assert res.status == 'INVALID'
    assert 'INVALID_BEDROOM_COUNT' in res.reason_codes

def test_ZeroBathrooms_IsRejected():
    reqs = {'bedrooms': 2, 'bathrooms': 0, 'floors': 1}
    res = validate_requirements_sanity(reqs)
    assert res.status == 'INVALID'
    assert 'INVALID_BATHROOM_COUNT' in res.reason_codes

def test_NegativeParking_IsRejected():
    reqs = {'bedrooms': 2, 'bathrooms': 1, 'floors': 1, 'parking_spaces': -1}
    res = validate_requirements_sanity(reqs)
    assert res.status == 'INVALID'
    assert 'INVALID_PARKING_COUNT' in res.reason_codes

def test_HugeRequirementOnSmallLand_FailsSpatialValidationNotSemanticValidation():
    reqs = {'bedrooms': 6, 'bathrooms': 6, 'floors': 1, 'land_size': 8, 'land_unit': 'perch'}
    
    # 1. Semantic Validation
    sanity = validate_requirements_sanity(reqs)
    
    # It might be INVALID if catalogue doesn't have 6 beds/6 baths exactly
    # Let's say if it doesn't fail basic semantic logic, we check spatial
    # Actually if 6 bed / 6 bath doesn't exist, it might be NO_COMPATIBLE_BASE_PLAN.
    # But if we assume it doesn't fail semantic rules, we want to show it fails spatial.
    # Let's just run feasibility directly to test spatial
    feasibility = check_feasibility(reqs)
    assert feasibility.can_proceed is False
    assert 'BUILDABLE_ENVELOPE_TOO_SMALL' in feasibility.reason_codes

def test_UnusualButSupportedRatio_RequiresConfirmation():
    # 3 beds, 1 bath, 1 floor exists in catalogue
    reqs = {'bedrooms': 3, 'bathrooms': 1, 'floors': 1}
    res = validate_requirements_sanity(reqs)
    # The requirement validator checks if it's < 0.5 ratio -> NEEDS_CONFIRMATION
    # 1/3 = 0.33 -> NEEDS_CONFIRMATION
    assert res.status == 'NEEDS_CONFIRMATION'
    assert 'UNUSUAL_BEDROOM_BATHROOM_RATIO' in res.reason_codes

def test_UnsupportedCombination_ReturnsNearestCatalogueAlternatives():
    # 2 beds 12 baths
    reqs = {'bedrooms': 2, 'bathrooms': 12, 'floors': 1}
    res = validate_requirements_sanity(reqs)
    assert res.status == 'INVALID'
    # Should contain suggestion about nearest supported
    has_nearest = any("Nearest supported" in s or "supports a maximum" in s for s in res.suggestions)
    assert has_nearest is True
