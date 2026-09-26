from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import INTERNAL_API_KEY

def test_internal_api_auth_missing_and_invalid():
    client = TestClient(app)
    
    # Missing API key
    response = client.post("/knowledge/search", json={"query": "test"})
    assert response.status_code == 403 or response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

    # Invalid API key
    response = client.post(
        "/knowledge/search", 
        json={"query": "test"},
        headers={"X-Internal-API-Key": "invalid-key"}
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

def test_internal_api_auth_valid():
    client = TestClient(app)
    
    # To test valid auth without triggering the DB, we mock the underlying service call
    with patch("app.knowledge.retrieval_service.search_knowledge_as_dicts") as mock_search:
        mock_search.return_value = []
        response = client.post(
            "/knowledge/search", 
            json={"query": "test", "top_k": 3},
            headers={"X-Internal-API-Key": INTERNAL_API_KEY}
        )
        assert response.status_code == 200
        assert response.json() == {"results": [], "count": 0}
