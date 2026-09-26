"""Seed and diversity contracts for the current validated-template flow."""
import pytest

from app.design.generation.diversity import geometry_fingerprint
from app.design.generation import generation_service as generation

PREFERENCES = {'bedrooms': 4, 'bathrooms': 2, 'floors': 2, 'style': 'modern'}
PLOT = {'plot_width_ft': 70, 'plot_length_ft': 75}


@pytest.fixture(autouse=True)
def deterministic_fallback(monkeypatch):
    monkeypatch.setattr(generation, 'get_available_design_provider', lambda: None)


def generate(seed, previous=None):
    return generation.generate_layout(
        20, 'flat', PREFERENCES, design_seed=seed, plot_constraints=PLOT,
        previous_design=previous.model_dump() if previous is not None else None,
        revision_reason='Generate Another' if previous is not None else None)


def test_same_seed_is_reproducible():
    first = generate(42)
    second = generate(42)
    assert first.candidate_summary['normalized_input'] == second.candidate_summary['normalized_input']
    assert first.candidate_summary['selected_plan_code'] == second.candidate_summary['selected_plan_code']
    assert geometry_fingerprint(first) == geometry_fingerprint(second)
    assert first.candidate_summary['generation_mode'] == 'deterministic_template_selection'


def test_different_seeds_do_not_require_different_geometry():
    # A single compatible geometry is a valid catalogue, regardless of seed.
    # Exercise the real catalogue's one-geometry 3-bedroom/single-floor coverage.
    fingerprints = set()
    for seed in (1, 2, 42):
        result = generation.generate_layout(
            20, 'flat', {'bedrooms': 3, 'bathrooms': 2, 'floors': 1, 'style': 'modern'}, design_seed=seed, plot_constraints=PLOT)
        assert result.design_seed == seed
        assert result.candidate_summary['generation_mode'] == 'deterministic_template_selection'
        assert result.candidate_status == 'VALID_HIGH_QUALITY'
        fingerprints.add(geometry_fingerprint(result))
    assert len(fingerprints) == 1


def test_generate_another_is_novel_without_changing_seed():
    previous = generate(42)
    result = generate(42, previous)
    assert result.design_seed == previous.design_seed
    assert result.geometry_fingerprint != previous.geometry_fingerprint
    assert result.candidate_summary['previous_fingerprint'] == previous.geometry_fingerprint
    assert result.candidate_status == 'VALID_HIGH_QUALITY'
