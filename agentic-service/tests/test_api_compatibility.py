from app.main import app

def test_api_route_compatibility():
    """Verify that all external API endpoints are correctly registered in the OpenAPI schema."""
    openapi_schema = app.openapi()
    paths = openapi_schema.get("paths", {})
    
    # Assert critical endpoints exist
    assert "/workflows/start" in paths, "Missing /workflows/start route"
    assert "post" in paths["/workflows/start"], "/workflows/start should be POST"
    
    assert "/workflows/resume" in paths, "Missing /workflows/resume route"
    assert "post" in paths["/workflows/resume"], "/workflows/resume should be POST"
    
    assert "/assistant/interpret" in paths, "Missing /assistant/interpret route"
    assert "post" in paths["/assistant/interpret"], "/assistant/interpret should be POST"
    
    assert "/knowledge/search" in paths, "Missing /knowledge/search route"
    assert "post" in paths["/knowledge/search"], "/knowledge/search should be POST"
    
    assert "/knowledge/seed" in paths, "Missing /knowledge/seed route"
    assert "post" in paths["/knowledge/seed"], "/knowledge/seed should be POST"

def test_health_routes():
    """Verify root and health endpoints."""
    openapi_schema = app.openapi()
    paths = openapi_schema.get("paths", {})
    
    assert "/" in paths
    assert "get" in paths["/"]
    
    assert "/health" in paths
    assert "get" in paths["/health"]
