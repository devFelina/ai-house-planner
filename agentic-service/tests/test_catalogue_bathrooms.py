import copy
import json

import pytest

from app.design.catalogue import base_plan_library as library
from app.design.program.room_counts import count_bathrooms
from scripts.catalogue import build_seed_catalogue as exporter


@pytest.fixture
def two_bath_plan():
    return next(plan for plan in json.loads(library.SEED_PATH.read_text())
                if (plan['bedrooms'], plan['bathrooms'], plan['floors']) == (4, 2, 2))


@pytest.mark.parametrize('declared', [1, 3, None])
def test_loader_rejects_bathroom_metadata_mismatch(two_bath_plan, tmp_path, monkeypatch, caplog, declared):
    source = copy.deepcopy(two_bath_plan)
    source['bathrooms'] = declared
    path = tmp_path / 'catalogue.json'
    path.write_text(json.dumps([source]))
    monkeypatch.setattr(library, 'SEED_PATH', path)
    assert library._load_seed_records() == []
    assert source['designCode'] in caplog.text
    assert 'bathroom count mismatch' in caplog.text
    assert 'actual 2' in caplog.text


def test_loader_accepts_exact_bathroom_count(two_bath_plan, tmp_path, monkeypatch):
    path = tmp_path / 'catalogue.json'
    path.write_text(json.dumps([two_bath_plan]))
    monkeypatch.setattr(library, 'SEED_PATH', path)
    records = library._load_seed_records()
    assert len(records) == 1
    assert records[0].bathrooms == 2
    assert records[0].plan_code == two_bath_plan['designCode']


def test_checked_catalogue_keeps_only_matching_metadata():
    sources = {plan['designCode']: plan for plan in json.loads(library.SEED_PATH.read_text())}
    records = library._load_seed_records()
    # The 39 historical bathroom-metadata mismatches have been resolved.
    assert len(records) == len(sources)
    for record in records:
        assert record.bathrooms == sources[record.plan_code]['bathrooms']
        assert record.bathrooms == count_bathrooms(json.loads(record.layout_json)['rooms'])


@pytest.mark.parametrize('configured,floors', [(1, 2), (1, 3), (2, 3)])
def test_seed_export_rejects_surplus_bathrooms(configured, floors):
    plan = exporter.gen_plan('test', 3, configured, floors, 'HILLSIDE_STEPPED', 5, 'hillside')
    valid, reason = exporter.validate_plan(plan, 'hillside')
    assert not valid
    assert reason == f'Bathroom count mismatch: configured {configured}, actual {floors}'


def test_seed_export_accepts_matching_bathrooms(two_bath_plan, monkeypatch):
    import scripts.catalogue.build_seed_catalogue
    from app.design.geometry.plot_constraints import PlotConstraints
    
    # Use a large enough plot so the plan fits geometrically without a BUILDABLE_ENVELOPE_VIOLATION.
    def mock_plot(*args, **kwargs):
        kwargs['plot_width_ft'] = 100
        kwargs['plot_length_ft'] = 100
        kwargs['terrain_type'] = 'flat'
        return PlotConstraints(*args, **kwargs)
        
    monkeypatch.setattr(scripts.catalogue.build_seed_catalogue, 'PlotConstraints', mock_plot)
    valid, reason = exporter.validate_plan(two_bath_plan, 'flat')
    assert valid, reason


def test_numbered_and_attached_bathrooms_share_counting_rule():
    rooms = [{'room_type': kind} for kind in ('bathroom', 'bathroom_2', 'bathroom_attached',
                                             'bathroom_storage', 'bedroom_1', 'bath_mat')]
    assert count_bathrooms(rooms) == 4
