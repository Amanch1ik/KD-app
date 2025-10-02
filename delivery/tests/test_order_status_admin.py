import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    return User.objects.create_user(username='customer', password='customerpass')


@pytest.fixture
def admin(db):
    return User.objects.create_user(username='admin', password='adminpass', is_staff=True)


def get_token(client, username, password):
    resp = client.post('/token/', {'username': username, 'password': password}, format='json')
    return resp.data.get('access') if resp.status_code == 200 else None


def test_admin_can_update_order_status(api_client, customer, admin, db):
    # login as customer to create an order
    api_client.force_authenticate(user=customer)
    from delivery.models import Restaurant, Category, Product
    rest = Restaurant.objects.create(name='AdminR', is_active=True, latitude=0.0, longitude=0.0)
    cat = Category.objects.create(is_active=True, name='Pizza', description='Pizza')
    prod = Product.objects.create(restaurant=rest, category=cat, name='Pepperoni', price=10.0, is_available=True)
    order_data = {
        'total_amount': 10.0,
        'delivery_address': 'Test Address',
        'phone_number': '+10000000000',
        'restaurant': rest.id,
        'payment_method': 'cash',
    }
    resp = api_client.post('/endpoints/orders/', order_data, format='json')
    assert resp.status_code in (200, 201)
    order_id = resp.json().get('id')
    assert order_id is not None

    # get admin token
    api_client.force_authenticate(user=admin)
    token = get_token(api_client, 'admin', 'adminpass')
    assert token

    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    resp2 = api_client.post(f'/endpoints/orders/{order_id}/update_status/', {'status': 'delivered'}, format='json')
    assert resp2.status_code in (200, 202)
    assert resp2.json().get('new_status') == 'delivered'


