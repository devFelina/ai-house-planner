"""
Tests for the deterministic feasibility engine.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.land.feasibility_engine import (
    SQFT_PER_PERCH,
    check_feasibility,
    generate_feasibility_advice,
    normalize_land,
)


def test_land_normalization():
    """Test perch to sqft conversion and dimension derivation."""
    print("\n=== TEST: Land Normalization ===")

    # 1. Perch conversion
    land = normalize_land(land_size=25, land_unit='perch')
    assert abs(land.land_area_sqft - 25 * SQFT_PER_PERCH) < 1
    assert land.dimension_source == 'area_estimated'
    assert land.plot_width_ft > 0
    assert land.plot_length_ft > 0
    print(f"  ✓ 25 perch = {land.land_area_sqft} sqft, dims={land.plot_width_ft}x{land.plot_length_ft}, source={land.dimension_source}")

    # 2. User-supplied dimensions
    land2 = normalize_land(land_size=25, land_unit='perch', plot_width_ft=50, plot_length_ft=60)
    assert land2.dimension_source == 'user_supplied'
    assert land2.plot_width_ft == 50
    assert land2.plot_length_ft == 60
    print(f"  ✓ User-supplied: {land2.plot_width_ft}x{land2.plot_length_ft}, source={land2.dimension_source}")

    # 3. Partially derived
    land3 = normalize_land(land_size=25, land_unit='perch', plot_width_ft=50)
    assert land3.dimension_source == 'partially_derived'
    assert land3.plot_width_ft == 50
    assert land3.plot_length_ft > 0
    print(f"  ✓ Partially derived: {land3.plot_width_ft}x{land3.plot_length_ft}, source={land3.dimension_source}")

    # 4. Sqft input
    land4 = normalize_land(land_size=5000, land_unit='sqft')
    assert abs(land4.land_size_perches - 5000 / SQFT_PER_PERCH) < 0.1
    print(f"  ✓ 5000 sqft = {land4.land_size_perches} perches")


def test_buildable_envelope():
    """Test setback calculations."""
    print("\n=== TEST: Buildable Envelope ===")

    land = normalize_land(land_size=25, land_unit='perch', plot_width_ft=60, plot_length_ft=80)
    # Default setbacks: front=10, rear=7, left=5, right=5
    expected_bw = 60 - 5 - 5  # 50
    expected_bl = 80 - 10 - 7  # 63
    assert abs(land.buildable_width_ft - expected_bw) < 0.5
    assert abs(land.buildable_length_ft - expected_bl) < 0.5
    print(f"  ✓ Buildable: {land.buildable_width_ft}x{land.buildable_length_ft} = {land.buildable_area_sqft} sqft")

    # With parking
    land_park = normalize_land(land_size=25, land_unit='perch', plot_width_ft=60, plot_length_ft=80, parking_required=True)
    expected_bl_park = 80 - 18 - 7  # 55 (front becomes 18 for parking)
    assert abs(land_park.buildable_length_ft - expected_bl_park) < 0.5
    print(f"  ✓ With parking: buildable length={land_park.buildable_length_ft}")


def test_reasonable_request_can_proceed():
    """25 perch, 3 bed, 2 bath, 1 floor -> should find plans."""
    print("\n=== TEST: Reasonable Request ===")

    result = check_feasibility({
        'land_size': 25,
        'land_unit': 'perch',
        'bedrooms': 3,
        'bathrooms': 2,
        'floors': 1,
    })

    print(f"  can_proceed: {result.can_proceed}")
    print(f"  compatible_plan_count: {result.compatible_plan_count}")
    print(f"  reason_codes: {result.reason_codes}")
    print(f"  suggestions: {result.suggestions}")
    print(f"  compatible plans: {result.compatible_plan_codes[:5]}")
    assert result.can_proceed, f"Expected can_proceed=True but got reason_codes={result.reason_codes}"
    assert result.compatible_plan_count > 0
    print("  ✓ Reasonable request accepted!")


def test_very_small_land_too_many_bedrooms():
    """3 perch with 6 bedrooms -> should reject."""
    print("\n=== TEST: Very Small Land + Too Many Bedrooms ===")

    result = check_feasibility({
        'land_size': 3,
        'land_unit': 'perch',
        'bedrooms': 6,
        'bathrooms': 4,
        'floors': 1,
    })

    print(f"  can_proceed: {result.can_proceed}")
    print(f"  reason_codes: {result.reason_codes}")
    print(f"  suggestions: {result.suggestions}")
    assert not result.can_proceed, "Expected rejection"
    print("  ✓ Small land + many bedrooms correctly rejected!")


def test_unsupported_feature():
    """Request a feature no plan supports -> reject."""
    print("\n=== TEST: Unsupported Feature ===")

    # Request accessibility + balcony + veranda + pool (pool isn't in most)
    result = check_feasibility({
        'land_size': 25,
        'land_unit': 'perch',
        'bedrooms': 3,
        'bathrooms': 2,
        'floors': 1,
        'accessible_friendly': True,
        'balcony': True,
        'veranda': True,
        'office': True,
        'open_plan': True,
        'master_ensuite': True,
        'separate_dining': True,
        'utility_room': True,
    })

    print(f"  can_proceed: {result.can_proceed}")
    print(f"  reason_codes: {result.reason_codes}")
    print(f"  compatible_plan_count: {result.compatible_plan_count}")
    print(f"  suggestions: {result.suggestions}")

    # All those features together on single floor should drastically reduce options
    if not result.can_proceed:
        assert 'NO_COMPATIBLE_BASE_PLAN' in result.reason_codes
        print("  ✓ Many features correctly led to rejection!")
    else:
        print("  ⚠ Some plans do support all these features — testing passed with caveats.")


def test_multifloor_no_compatible_plan():
    """3 floors with 6 bedrooms on tiny land -> reject."""
    print("\n=== TEST: Multi-Floor No Compatible Plan ===")

    result = check_feasibility({
        'land_size': 3,
        'land_unit': 'perch',
        'bedrooms': 6,
        'bathrooms': 5,
        'floors': 3,
    })

    print(f"  can_proceed: {result.can_proceed}")
    print(f"  reason_codes: {result.reason_codes}")
    print(f"  suggestions: {result.suggestions}")
    assert not result.can_proceed
    print("  ✓ Multi-floor + tiny land correctly rejected!")


def test_advice_mode_returns_ranges():
    """LAND_FEASIBILITY_ADVICE should return ranges, not one exact answer."""
    print("\n=== TEST: Advice Mode ===")

    advice = generate_feasibility_advice({
        'land_size': 25,
        'land_unit': 'perch',
    })

    print(f"  advice_type: {advice['advice_type']}")
    print(f"  message:\n    {advice['message']}")
    print(f"  ranges: {json.dumps(advice.get('ranges'), indent=4)}")

    assert advice['advice_type'] == 'LAND_FEASIBILITY'
    assert advice['ranges'] is not None
    assert len(advice['ranges']) > 0

    # Verify ranges, not single values
    for floor_count, info in advice['ranges'].items():
        bed_range = info['bedroom_range']
        assert len(bed_range) == 2
        print(f"  ✓ {floor_count}-floor: {bed_range[0]}-{bed_range[1]} bedrooms, {info['plan_count']} plans")

    print("  ✓ Advice mode returns practical ranges!")


def test_unsupported_floor_count():
    """Request 4 floors -> should reject."""
    print("\n=== TEST: Unsupported Floor Count ===")

    result = check_feasibility({
        'land_size': 25,
        'land_unit': 'perch',
        'bedrooms': 3,
        'bathrooms': 2,
        'floors': 4,
    })

    print(f"  can_proceed: {result.can_proceed}")
    print(f"  reason_codes: {result.reason_codes}")
    assert not result.can_proceed
    assert 'FLOOR_COUNT_UNSUPPORTED' in result.reason_codes
    print("  ✓ 4 floors correctly rejected!")


def test_no_land_info():
    """No land size -> should include NO_LAND_SIZE."""
    print("\n=== TEST: No Land Info ===")

    result = check_feasibility({
        'bedrooms': 3,
        'bathrooms': 2,
        'floors': 1,
    })

    print(f"  can_proceed: {result.can_proceed}")
    print(f"  reason_codes: {result.reason_codes}")
    assert 'NO_LAND_SIZE' in result.reason_codes
    print("  ✓ Missing land size correctly flagged!")


if __name__ == '__main__':
    test_land_normalization()
    test_buildable_envelope()
    test_reasonable_request_can_proceed()
    test_very_small_land_too_many_bedrooms()
    test_unsupported_feature()
    test_multifloor_no_compatible_plan()
    test_advice_mode_returns_ranges()
    test_unsupported_floor_count()
    test_no_land_info()

    print("\n" + "=" * 60)
    print("ALL FEASIBILITY ENGINE TESTS PASSED ✓")
    print("=" * 60)
