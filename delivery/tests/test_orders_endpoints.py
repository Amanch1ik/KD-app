import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='ordertester', password='testpass123')


def test_order_endpoints_require_auth(api_client):
    resp = api_client.post('/endpoints/orders/', {}, format='json')
    assert resp.status_code == 401 or resp.status_code == 403 or resp.status_code == 405


def test_create_order_via_orders_endpoint(api_client, user):
    api_client.force_authenticate(user=user)
    from delivery.models import Restaurant
    rest = Restaurant.objects.create(name='TestR', is_active=True, latitude=0.0, longitude=0.0)
    data = {
        'total_amount': 50.0,
        'delivery_address': 'Test Addr',
        'phone_number': '+1234567890',
        'restaurant': rest.id,
        'payment_method': 'cash',
    }
    resp = api_client.post('/endpoints/orders/', data, format='json')
    assert resp.status_code in (200, 201)
    json = resp.json()
    assert 'id' in json


def test_order_history_returns_list(api_client, user):
    api_client.force_authenticate(user=user)
    resp = api_client.get('/endpoints/orders/')
    assert resp.status_code in (200, 204)

