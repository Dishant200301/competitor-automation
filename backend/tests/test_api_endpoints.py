import uuid
import pytest
from fastapi.testclient import TestClient
from app.database.connection import DatabaseClient
from app.api import routes
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    database=DatabaseClient('sqlite',str(tmp_path/'test.db'))
    monkeypatch.setattr(routes,'db',database)
    async def noop(run_id): pass
    monkeypatch.setattr(routes.orchestrator,'execute_run_async',noop)
    return TestClient(app)


def test_health_endpoint(client):
    assert client.get('/api/health').status_code==200


def test_create_and_get_research_run(client):
    res=client.post('/api/research',json={'source_input':'https://example.com'})
    assert res.status_code==201
    run_id=res.json()['research_run_id']
    assert client.get(f'/api/research/{run_id}/status').json()['status']=='queued'
    assert client.get(f'/api/research/{run_id}/summary').status_code==200
    assert client.get(f'/api/research/{run_id}/report/pdf').status_code==409
    assert client.post(f'/api/research/{run_id}/generate-pdf').status_code==409


def test_invalid_and_missing_runs(client):
    assert client.get('/api/research/not-a-uuid/report/pdf').status_code==422
    assert client.get(f'/api/research/{uuid.uuid4()}/report/pdf').status_code==404
    assert client.post('/api/research',json={'source_input':'http://127.0.0.1'}).status_code==400
    assert client.post('/api/research',json={'source_input':'file:///etc/passwd'}).status_code==400


def test_no_google_docs_route(client):
    assert client.post(f'/api/research/{uuid.uuid4()}/generate-google-doc').status_code==404


def test_single_call_execution(client):
    res = client.post('/api/research/execute', json={'source_input': 'https://example.com'})
    assert res.status_code == 201 or res.status_code == 200
    data = res.json()
    assert 'run' in data
    assert 'competitors' in data


def test_docx_report_endpoint(client):
    assert client.get(f'/api/research/{uuid.uuid4()}/report/docx').status_code in (404, 409)

