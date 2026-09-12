"""Unit tests never call paid APIs or write workflow state to a local server."""
import pytest


@pytest.fixture(autouse=True)
def offline_services(monkeypatch):
    monkeypatch.setattr('app.tools.layout_generation_tool.GOOGLE_API_KEY', '')
    monkeypatch.setattr('app.tools.vision_classify_tool.GOOGLE_API_KEY', '')
    monkeypatch.setattr('app.agents.land_analysis_agent._persist_terrain', lambda state: None)
    monkeypatch.setattr('app.agents.design_agent._persist_failure', lambda state: None)
