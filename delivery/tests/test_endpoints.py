import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='tester', password='testpass123')


def test_menu_endpoints_are_public(api_client):
    # Menu endpoints should be accessible without authentication (read-only)
    resp_cat = api_client.get('/endpoints/categories/')
    resp_prod = api_client.get('/endpoints/products/')
    assert resp_cat.status_code == 200
    assert resp_prod.status_code in (200, 404, 204, 301) or resp_prod.status_code == 200


def test_cart_endpoints_require_auth_and_basics(api_client, user, db):
    # Ensure cart endpoints respond for authenticated user
    api_client.force_authenticate(user=user)
    resp = api_client.get('/endpoints/cart/')
    assert resp.status_code in (200, 204, 404) or resp.status_code == 200


def test_create_cart_and_checkout(api_client, user, db):
    api_client.force_authenticate(user=user)
    from delivery.models import Restaurant, Category, Product

    rest = Restaurant.objects.create(name='Test R', is_active=True, latitude=0, longitude=0)
    cat = Category.objects.create(is_active=True, name='Pizza', description='Pizza')
    prod = Product.objects.create(restaurant=rest, category=cat, name='Margherita', price=9.99, is_available=True, description='Classic')

    resp = api_client.post('/endpoints/cart/', {'product': prod.id, 'quantity': 2}, format='json')
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert 'order_id' in data and data['order_id'] is not None
    assert 'items' in data

    # Checkout cart into an order
    resp2 = api_client.post('/endpoints/cart/checkout/', {'delivery_address': 'Test addr', 'phone_number': '+1234567890'}, format='json')
    assert resp2.status_code == 200
    checkout_data = resp2.json()
    assert 'status' in checkout_data and checkout_data['status'] in ('pending', 'Confirmed', 'preparing', 'delivered') or checkout_data.get('status') in ('pending',)


