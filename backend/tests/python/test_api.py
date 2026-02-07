import pytest
from fastapi.testclient import TestClient

def test_ping(client):
    """Test the health check endpoint."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_recommend_validation_error(client):
    """Test that invalid request body returns 422."""
    response = client.post("/api/v1/recommend", json={"invalid": "data"})
    assert response.status_code == 422

def test_search_movies(client):
    """Test the search endpoint."""
    # This might fail if app state is not initialized in TestClient correctly 
    # for dependencies, but let's try the basic route.
    response = client.get("/api/v1/movies/search?q=Toy")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
