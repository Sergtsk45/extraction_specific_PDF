"""Tests for GET /health endpoint of invoice-extractor."""


def test_health_returns_200(client):
    response = client.get('/health')
    assert response.status_code == 200


def test_health_status_is_ok(client):
    data = client.get('/health').get_json()
    assert data['status'] == 'ok'


def test_health_service_name(client):
    data = client.get('/health').get_json()
    assert data['service'] == 'invoice-extractor'


def test_health_version_present(client):
    data = client.get('/health').get_json()
    assert 'version' in data


def test_health_version_value(client):
    data = client.get('/health').get_json()
    assert data['version'] == '1.0.0'
