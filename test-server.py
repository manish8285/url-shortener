import pytest
from server import app
import redis
import os
from datetime import datetime, timedelta

# Create a test client for the Flask application
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_shorten_url_valid(client):
    response = client.post(
        "/url/shorten",
        json={"url": "https://www.example.com"}
    )
    assert response.status_code == 200
    assert "short_url" in response.get_json()
    assert response.get_json()["short_url"].startswith("http://")

def test_shorten_url_invalid(client):
    response = client.post(
        "/url/shorten",
        json={"url": "not-a-valid-url"}
    )
    assert response.status_code == 400

def test_custom_slug(client):
    response = client.post(
        "/url/shorten",
        json={
            "url": "https://www.example.com",
            "custom_slug": "my-custom-url"
        }
    )
    assert response.status_code == 200
    assert "my-custom-url" in response.get_json()["short_url"]

def test_expiring_url(client):
    # Create URL with 1 day expiration
    response = client.post(
        "/url/shorten",
        json={
            "url": "https://www.example.com",
            "expiration_days": 1
        }
    )
    assert response.status_code == 200
    short_url = response.get_json()["short_url"]
    
    # Get the shortened part
    slug = short_url.split("/")[-1]
    
    # Verify redirect works
    response = client.get(f"/r/{slug}", follow_redirects=False)
    assert response.status_code == 302  # Flask uses 302 for redirects

def test_stats(client):
    # Create a URL first
    response = client.post(
        "/url/shorten",
        json={"url": "https://www.example.com"}
    )
    short_url = response.get_json()["short_url"].split("/")[-1]
    
    # Access it a few times
    for _ in range(3):
        client.get(f"/r/{short_url}")
    
    # Check stats
    response = client.get(f"/stats/{short_url}")
    assert response.status_code == 200
    assert response.get_json()["access_count"] == 3
