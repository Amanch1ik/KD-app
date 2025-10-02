from django.test import TestCase, override_settings
from django.utils.translation import activate, get_language, gettext as _
from django.urls import reverse
from rest_framework.test import APIClient
from delivery.models import Category, Restaurant, Product

class InternationalizationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Создаем тестовые объекты с переводами
        self.category = Category.objects.create(
            name='Фаст-фуд', 
            name_ru='Фаст-фуд', 
            name_ky='Тез тамак', 
            name_en='Fast Food'
        )
        
        self.restaurant = Restaurant.objects.create(
            name='Вкусная еда', 
            name_ru='Вкусная еда', 
            name_ky='Даамдуу тамак', 
            name_en='Tasty Food'
        )
        
        self.product = Product.objects.create(
            name='Гамбургер', 
            name_ru='Гамбургер', 
            name_ky='Гамбургер', 
            name_en='Hamburger',
            description='Сочный бургер', 
            description_ru='Сочный бургер', 
            description_ky='Жумшак бургер', 
            description_en='Juicy burger',
            price=500,
            restaurant=self.restaurant,
            category=self.category
        )

    def test_category_translations(self):
        """Проверка переводов для категории"""
        activate('ru')
        self.assertEqual(self.category.name, 'Фаст-фуд')
        
        activate('ky')
        self.assertEqual(self.category.name, 'Тез тамак')
        
        activate('en')
        self.assertEqual(self.category.name, 'Fast Food')

    def test_restaurant_translations(self):
        """Проверка переводов для ресторана"""
        activate('ru')
        self.assertEqual(self.restaurant.name, 'Вкусная еда')
        
        activate('ky')
        self.assertEqual(self.restaurant.name, 'Даамдуу тамак')
        
        activate('en')
        self.assertEqual(self.restaurant.name, 'Tasty Food')

    def test_product_translations(self):
        """Проверка переводов для продукта"""
        activate('ru')
        self.assertEqual(self.product.name, 'Гамбургер')
        self.assertEqual(self.product.description, 'Сочный бургер')
        
        activate('ky')
        self.assertEqual(self.product.name, 'Гамбургер')
        self.assertEqual(self.product.description, 'Жумшак бургер')
        
        activate('en')
        self.assertEqual(self.product.name, 'Hamburger')
        self.assertEqual(self.product.description, 'Juicy burger')

    @override_settings(LANGUAGE_CODE='ru')
    def test_language_middleware(self):
        """Проверка работы middleware переключения языков"""
        response = self.client.get(reverse('set-language'), {'language': 'ky'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_language(), 'ky')

    def test_gettext_translations(self):
        """Проверка работы gettext для переводов"""
        activate('ru')
        self.assertEqual(_('Welcome'), 'Добро пожаловать')
        
        activate('ky')
        self.assertEqual(_('Welcome'), 'Кош келиңиз')
        
        activate('en')
        self.assertEqual(_('Welcome'), 'Welcome')

    def test_serializer_translations(self):
        """Проверка переводов в сериализаторах"""
        from delivery.serializers import CategorySerializer, ProductSerializer
        
        activate('ru')
        category_serializer = CategorySerializer(self.category)
        product_serializer = ProductSerializer(self.product)
        
        self.assertEqual(category_serializer.data['name'], 'Фаст-фуд')
        self.assertEqual(product_serializer.data['name'], 'Гамбургер')
        self.assertEqual(product_serializer.data['description'], 'Сочный бургер')

    def test_admin_translations(self):
        """Проверка переводов в административном интерфейсе"""
        from django.contrib.admin import site
        from delivery.admin import CategoryAdmin, ProductAdmin
        
        category_admin = CategoryAdmin(Category, site)
        product_admin = ProductAdmin(Product, site)
        
        activate('ru')
        self.assertIn('Название', str(category_admin.list_display))
        
        activate('ky')
        self.assertIn('Аталышы', str(category_admin.list_display))
        
        activate('en')
        self.assertIn('Name', str(category_admin.list_display))
