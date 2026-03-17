"""Tests for GET /health and /health/details endpoints of spec-converterv2."""


def test_health_returns_200(client):
    response = client.get('/health')
    assert response.status_code == 200


def test_health_status_is_ok(client):
    data = client.get('/health').get_json()
    assert data['status'] == 'ok'


def test_health_service_name(client):
    data = client.get('/health').get_json()
    assert data['service'] == 'spec-converterv2'


def test_health_version_present(client):
    data = client.get('/health').get_json()
    assert 'version' in data


def test_health_version_value(client):
    data = client.get('/health').get_json()
    assert data['version'] == '2.0.0'


def test_health_no_provider_field(client):
    data = client.get('/health').get_json()
    assert 'provider' not in data


def test_health_no_model_field(client):
    data = client.get('/health').get_json()
    assert 'model' not in data


def test_health_no_configured_field(client):
    data = client.get('/health').get_json()
    assert 'configured' not in data


def test_health_details_forbidden_from_non_localhost(client):
    response = client.get('/health/details', environ_base={'REMOTE_ADDR': '1.2.3.4'})
    assert response.status_code == 403
