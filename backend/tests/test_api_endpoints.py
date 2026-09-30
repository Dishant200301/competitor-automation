import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "competitor-intelligence"

def test_create_and_get_research_run():
    # POST
    payload = {
        "source_type": "website",
        "source_input": "https://example.com"
    }
    create_res = client.post("/api/research", json=payload)
    assert create_res.status_code == 201
    create_data = create_res.json()
    run_id = create_data["research_run_id"]
    assert run_id is not None
    assert create_data["status"] == "queued"

    # GET Status
    status_res = client.get(f"/api/research/{run_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["id"] == run_id
    assert status_data["source_input"] == "https://example.com"

    # GET Summary
    summary_res = client.get(f"/api/research/{run_id}/summary")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert "run" in summary_data
    assert "competitors" in summary_data
