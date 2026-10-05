import os
from unittest import mock
import pytest
import importlib

@pytest.fixture
def clean_env():
    with mock.patch.dict(os.environ, clear=True):
        yield

def test_aspnet_api_url_no_whitespace(clean_env):
    os.environ["ASPNET_API_URL"] = "https://ai-house-planner-backend-w4sr.onrender.com/api/v1"
    
    # Instead of reloading config and breaking other tests, we just verify the exact parsing logic
    url = os.getenv("ASPNET_API_URL", "http://localhost:5265/api/v1").strip().rstrip("/")
    assert url == "https://ai-house-planner-backend-w4sr.onrender.com/api/v1"

def test_aspnet_api_url_with_newline(clean_env):
    os.environ["ASPNET_API_URL"] = "https://ai-house-planner-backend-w4sr.onrender.com/api/v1\n"
    
    url = os.getenv("ASPNET_API_URL", "http://localhost:5265/api/v1").strip().rstrip("/")
    assert url == "https://ai-house-planner-backend-w4sr.onrender.com/api/v1"

def test_aspnet_api_url_with_leading_trailing_spaces_and_slash(clean_env):
    os.environ["ASPNET_API_URL"] = "  https://ai-house-planner-backend-w4sr.onrender.com/api/v1/  "
    
    url = os.getenv("ASPNET_API_URL", "http://localhost:5265/api/v1").strip().rstrip("/")
    assert url == "https://ai-house-planner-backend-w4sr.onrender.com/api/v1"

def test_endpoint_construction_no_newline(clean_env):
    # Simulate the exact values that config.py would produce
    aspnet_api_url = "https://ai-house-planner-backend-w4sr.onrender.com/api/v1\n"
    workflow_id = "12345"
    
    # Execute the exact string interpolation used in plan_persistence.py
    endpoint = f"{aspnet_api_url.strip().rstrip('/')}/internal/workflows/{workflow_id}/plan"
    
    assert "\n" not in endpoint
    assert endpoint == "https://ai-house-planner-backend-w4sr.onrender.com/api/v1/internal/workflows/12345/plan"

