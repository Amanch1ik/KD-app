from django.test import TestCase
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date, timedelta
from decimal import Decimal

from ..models import (
    Category, 
    Restaurant, 
    Product, 
    Order, 
    DeliveryPerson, 
    UserProfile, 
    OrderItem, 
    Rating
)

class ModelTestCase(TestCase):
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
            is_active=True,
            avg_rating=4.5
        )
        
        self.product = Product.objects.create(
            name='Тестовый бургер',
            price=Decimal('10.50'),
            restaurant=self.restaurant,
            category=self.category,
            is_available=True
        )

    def test_category_creation(self):
        """Тест создания категории"""
        self.assertEqual(self.category.name, 'Фаст-фуд')
        self.assertTrue(self.category.is_active)
        self.assertEqual(str(self.category), 'Фаст-фуд')

    def test_restaurant_creation(self):
        """Тест создания ресторана"""
        self.assertEqual(self.restaurant.name, 'Тестовый ресторан')
        self.assertEqual(self.restaurant.partner_user, self.user)
        self.assertTrue(self.restaurant.is_active)
        self.assertEqual(self.restaurant.avg_rating, 4.5)

    def test_product_creation(self):
        """Тест создания продукта"""
        self.assertEqual(self.product.name, 'Тестовый бургер')
        self.assertEqual(self.product.price, Decimal('10.50'))
        self.assertEqual(self.product.restaurant, self.restaurant)
        self.assertEqual(self.product.category, self.category)
        self.assertTrue(self.product.is_available)

    def test_order_creation(self):
        """Тест создания заказа"""
        order = Order.objects.create(
            customer=self.user,
            restaurant=self.restaurant,
            status='pending',
            payment_method='cash',
            delivery_address='Test Address',
            phone_number='+996555123456',
            total_amount=Decimal('25.00')
        )
        
        # Создаем элемент заказа
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=self.product.price
        )

        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.total_amount, Decimal('25.00'))
        self.assertEqual(order.items.count(), 1)

    def test_delivery_person_creation(self):
        """Тест создания курьера"""
        delivery_person = DeliveryPerson.objects.create(
            user=self.user,
            phone_number='+996555123456',
            vehicle_type='bicycle',
            status='available',
            is_available=True
        )

        self.assertEqual(delivery_person.user, self.user)
        self.assertEqual(delivery_person.vehicle_type, 'bicycle')
        self.assertTrue(delivery_person.is_available)

    def test_user_profile_creation(self):
        """Тест создания профиля пользователя"""
        profile = UserProfile.objects.create(
            user=self.user,
            role='client',
            phone_number='+996555123456'
        )

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.role, 'client')
        self.assertEqual(profile.phone_number, '+996555123456')

    def test_rating_creation(self):
        """Тест создания рейтинга"""
        order = Order.objects.create(
            customer=self.user,
            restaurant=self.restaurant,
            status='delivered',
            payment_method='cash',
            delivery_address='Test Address',
            phone_number='+996555123456',
            total_amount=Decimal('25.00')
        )

        delivery_person = DeliveryPerson.objects.create(
            user=self.user,
            vehicle_type='bicycle'
        )

        rating = Rating.objects.create(
            order=order,
            courier=delivery_person,
            restaurant=self.restaurant,
            score=4,
            comment='Хорошая доставка'
        )

        self.assertEqual(rating.order, order)
        self.assertEqual(rating.courier, delivery_person)
        self.assertEqual(rating.score, 4)
        self.assertEqual(rating.comment, 'Хорошая доставка')

    def test_model_validation(self):
        """Тест валидации моделей"""
        # Проверка создания категории с пустым именем
        with self.assertRaises(ValidationError):
            Category.objects.create(name='')

        # Проверка создания продукта с отрицательной ценой
        with self.assertRaises(ValidationError):
            Product.objects.create(
                name='Невалидный продукт',
                price=Decimal('-10.00'),
                restaurant=self.restaurant,
                category=self.category
            )

        # Проверка создания заказа с некорректным номером телефона
        with self.assertRaises(ValidationError):
            Order.objects.create(
                customer=self.user,
                restaurant=self.restaurant,
                status='pending',
                payment_method='cash',
                delivery_address='Test Address',
                phone_number='invalid_number',
                total_amount=Decimal('25.00')
            )

class UserProfileModelTest(TestCase):
    def setUp(self):
        """
        Подготовка данных для тестирования
        """
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            role='client',
            email='test@example.com',
            preferred_language='ru',
            phone_number='+996555123456'
        )

    def test_create_user_profile(self):
        """
        Тест создания профиля пользователя
        """
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.role, 'client')
        self.assertEqual(self.profile.email, 'test@example.com')
        self.assertEqual(self.profile.preferred_language, 'ru')
        self.assertEqual(self.profile.phone_number, '+996555123456')

    def test_date_of_birth_validation(self):
        """
        Тест валидации даты рождения
        """
        # Дата рождения в будущем
        with self.assertRaises(ValidationError):
            future_date = date.today() + timedelta(days=1)
            self.profile.date_of_birth = future_date
            self.profile.full_clean()

        # Дата рождения для несовершеннолетнего
        with self.assertRaises(ValidationError):
            young_date = date.today() - timedelta(days=365 * 10)
            self.profile.date_of_birth = young_date
            self.profile.full_clean()

        # Корректная дата рождения
        valid_date = date.today() - timedelta(days=365 * 25)
        self.profile.date_of_birth = valid_date
        self.profile.full_clean()  # Не должно вызывать исключение

    def test_email_validation(self):
        """
        Тест валидации email
        """
        # Некорректный email
        with self.assertRaises(ValidationError):
            self.profile.email = 'invalid_email'
            self.profile.full_clean()

        # Корректный email
        self.profile.email = 'valid_email@example.com'
        self.profile.full_clean()  # Не должно вызывать исключение

    def test_phone_number_validation(self):
        """
        Тест валидации номера телефона
        """
        # Некорректный номер телефона
        with self.assertRaises(ValidationError):
            self.profile.phone_number = '123'
            self.profile.full_clean()

        # Корректный номер телефона
        self.profile.phone_number = '+996555123456'
        self.profile.full_clean()  # Не должно вызывать исключение

    def test_social_links_validation(self):
        """
        Тест валидации социальных ссылок
        """
        # Некорректные социальные ссылки
        with self.assertRaises(ValidationError):
            self.profile.social_links = ['https://example.com']
            self.profile.full_clean()

        # Корректные социальные ссылки
        self.profile.social_links = [
            'https://facebook.com/testuser',
            'https://instagram.com/testuser'
        ]
        self.profile.full_clean()  # Не должно вызывать исключение

    def test_profile_picture_validation(self):
        """
        Тест валидации фотографии профиля
        """
        # Создаем тестовое изображение
        test_image = SimpleUploadedFile(
            name='test_image.jpg', 
            content=b'', 
            content_type='image/jpeg'
        )
        self.profile.profile_picture = test_image
        self.profile.full_clean()  # Не должно вызывать исключение

    def test_notification_settings(self):
        """
        Тест настроек уведомлений
        """
        self.profile.notification_settings = ['email', 'sms']
        self.profile.full_clean()  # Не должно вызывать исключение

    def test_order_preferences(self):
        """
        Тест предпочтений заказов
        """
        self.profile.order_preferences = {
            'cuisine_type': 'italian',
            'max_price': 1000
        }
        self.profile.full_clean()  # Не должно вызывать исключение
