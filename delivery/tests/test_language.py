import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def test_set_language_valid_ru(api_client):
    resp = api_client.get('/set-language/', {'language': 'ru'})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('language') == 'ru'
    assert data.get('status') == 'success'


def test_set_language_valid_ky_en(api_client):
    for lang in ['ky', 'en']:
        resp = api_client.get('/set-language/', {'language': lang})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get('language') == lang
        assert data.get('status') == 'success'


def test_set_language_invalid(api_client):
    resp = api_client.get('/set-language/', {'language': 'uz'})
    assert resp.status_code == 400

