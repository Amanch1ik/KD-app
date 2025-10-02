from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from ..models import Order, DeliveryPerson, Restaurant, Product, Category
from ..services import (
    assign_available_courier, 
    calculate_delivery_fee, 
    validate_order_creation
)

class ServiceTestCase(TestCase):
    def setUp(self):
        # Создание тестовых данных
        self.user = User.objects.create_user(
            username='testuser', 
            password='12345'
        )
        
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

        # Создаем курьеров
        self.courier1 = DeliveryPerson.objects.create(
            user=User.objects.create_user(username='courier1', password='12345'),
            vehicle_type='bicycle',
            status='available',
            is_available=True
        )
        
        self.courier2 = DeliveryPerson.objects.create(
            user=User.objects.create_user(username='courier2', password='12345'),
            vehicle_type='motorcycle',
            status='available',
            is_available=True
        )

    def test_assign_available_courier(self):
        """Тест назначения доступного курьера"""
        order = Order.objects.create(
            customer=self.user,
            restaurant=self.restaurant,
            status='pending',
            payment_method='cash',
            delivery_address='Test Address',
            phone_number='+996555123456',
            total_amount=Decimal('25.00')
        )

        # Проверяем, что курьер назначен
        result = assign_available_courier(order)
        self.assertTrue(result)
        
        # Перезагружаем заказ
        order.refresh_from_db()
        
        # Проверяем, что курьер назначен и его статус изменился
        self.assertIsNotNone(order.delivery_person)
        self.assertEqual(order.status, 'assigned')
        
        # Проверяем, что курьер больше не доступен
        courier = order.delivery_person
        self.assertEqual(courier.status, 'busy')
        self.assertFalse(courier.is_available)

    def test_calculate_delivery_fee(self):
        """Тест расчета стоимости доставки"""
        # Тест для маленькой суммы заказа
        small_order_amount = Decimal('10.00')
        small_fee = calculate_delivery_fee(small_order_amount)
        self.assertGreater(small_fee, Decimal('0'))
        
        # Тест для большой суммы заказа
        large_order_amount = Decimal('100.00')
        large_fee = calculate_delivery_fee(large_order_amount)
        self.assertLess(large_fee, Decimal('5.00'))
        
        # Тест для бесплатной доставки
        free_delivery_amount = Decimal('50.00')
        free_fee = calculate_delivery_fee(free_delivery_amount)
        self.assertEqual(free_fee, Decimal('0'))

    def test_validate_order_creation(self):
        """Тест валидации создания заказа"""
        # Успешный сценарий
        valid_order_data = {
            'customer': self.user,
            'restaurant': self.restaurant,
            'total_amount': Decimal('25.00'),
            'delivery_address': 'Test Address',
            'phone_number': '+996555123456',
            'payment_method': 'cash'
        }
        
        result = validate_order_creation(valid_order_data)
        self.assertTrue(result['is_valid'])
        
        # Сценарий с недопустимой суммой заказа
        invalid_amount_data = valid_order_data.copy()
        invalid_amount_data['total_amount'] = Decimal('-10.00')
        
        result = validate_order_creation(invalid_amount_data)
        self.assertFalse(result['is_valid'])
        self.assertIn('total_amount', result['errors'])
        
        # Сценарий с некорректным номером телефона
        invalid_phone_data = valid_order_data.copy()
        invalid_phone_data['phone_number'] = 'invalid_number'
        
        result = validate_order_creation(invalid_phone_data)
        self.assertFalse(result['is_valid'])
        self.assertIn('phone_number', result['errors'])
        
        # Сценарий с отсутствием адреса доставки
        invalid_address_data = valid_order_data.copy()
        invalid_address_data['delivery_address'] = ''
        
        result = validate_order_creation(invalid_address_data)
        self.assertFalse(result['is_valid'])
        self.assertIn('delivery_address', result['errors'])
