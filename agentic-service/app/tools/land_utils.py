"""
Centralized land measurement utilities.
Single source of truth for perch-to-sqft conversion and coverage calculations.
"""

# Sri Lankan land measurement: 1 perch = 272.25 square feet
SQFT_PER_PERCH = 272.25

# Maximum built-up area as a fraction of total land area (65% coverage rule)
MAX_COVERAGE_RATIO = 0.65


def perches_to_sqft(perches: float) -> float:
    """Convert land size from perches to square feet."""
    return perches * SQFT_PER_PERCH


def max_buildable_area(land_size_perches: float) -> float:
    """
    Calculate the maximum total built-up area allowed for a given land size.
    Built-up area = total floor area across all floors (not just ground footprint).
    """
    return perches_to_sqft(land_size_perches) * MAX_COVERAGE_RATIO
