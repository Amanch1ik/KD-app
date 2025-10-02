from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from ..models import (
    Category, 
    Restaurant, 
    Product, 
    Order, 
    DeliveryPerson, 
    UserProfile
)

class ViewTestCase(TestCase):
    def setUp(self):
        # Создаем клиент для тестирования API
        self.client = APIClient()

        # Создаем тестовых пользователей
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com',
            password='testpassword123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staffuser', 
            email='staff@example.com',
            password='staffpassword123',
            is_staff=True
        )

        # Создаем профиль курьера
        self.courier = DeliveryPerson.objects.create(
            user=User.objects.create_user(
                username='courier', 
                password='courierpassword123'
            ),
            vehicle_type='bicycle',
            status='available',
            is_available=True
        )

        # Создаем тестовые данные
        self.category = Category.objects.create(
            name='Фаст-фуд',
            is_active=True
        )
        
        self.restaurant = Restaurant.objects.create(
            name='Тестовый ресторан',
            partner_user=self.user,
            is_active=True
        )
        
        self.product = Product.objects.create(
            name='Тестовый бургер',
            price=Decimal('10.50'),
            restaurant=self.restaurant,
            category=self.category,
            is_available=True
        )

    def test_user_registration(self):
        """Тест регистрации пользователя"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'strongpassword123',
            'password2': 'strongpassword123'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('access', response.data)

    def test_user_login(self):
        """Тест аутентификации пользователя"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_product_list(self):
        """Тест получения списка продуктов"""
        url = reverse('product-list')
        
        # Неавторизованный пользователь
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Авторизация
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_order_creation(self):
        """Тест создания заказа"""
        url = reverse('order-list')
        
        # Авторизация
        self.client.force_authenticate(user=self.user)
        
        data = {
            'restaurant': self.restaurant.id,
            'total_amount': Decimal('25.50'),
            'delivery_address': 'Test Address',
            'phone_number': '+996555123456',
            'payment_method': 'cash'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer'], self.user.id)
        self.assertEqual(response.data['restaurant'], self.restaurant.id)

    def test_courier_order_assignment(self):
        """Тест назначения заказа курьеру"""
        # Создаем заказ
        order = Order.objects.create(
            customer=self.user,
            restaurant=self.restaurant,
            status='pending',
            payment_method='cash',
            delivery_address='Test Address',
            phone_number='+996555123456',
            total_amount=Decimal('25.00')
        )
        
        # Авторизация курьера
        self.client.force_authenticate(user=self.courier.user)
        
        url = reverse('order-take-order', kwargs={'pk': order.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Перезагружаем заказ
        order.refresh_from_db()
        self.assertEqual(order.delivery_person, self.courier)
        self.assertEqual(order.status, 'assigned')

    def test_user_profile_update(self):
        """Тест обновления профиля пользователя"""
        url = reverse('user-profile')
        
        # Авторизация
        self.client.force_authenticate(user=self.user)
        
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'profile': {
                'phone_number': '+996555987654'
            }
        }
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем обновленные данные
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertEqual(response.data['profile']['phone_number'], '+996555987654')

    def test_unauthorized_access(self):
        """Тест доступа к защищенным эндпоинтам без авторизации"""
        urls = [
            reverse('order-list'),
            reverse('user-profile'),
            reverse('payout-list')
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
