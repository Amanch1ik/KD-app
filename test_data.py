#!/usr/bin/env python
"""
Скрипт для добавления тестовых данных в базу данных
Запуск: python test_data.py
"""

import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karakoldelivery.settings')
django.setup()

from delivery.models import Category, Product, DeliveryZone, Restaurant, DeliveryPerson
from django.contrib.auth.models import User

def create_test_data():
    print("Создание тестовых данных...")
    
    # Создаем категории
    categories_data = [
        {"name": "Пицца", "description": "Итальянская пицца с различными начинками"},
        {"name": "Суши", "description": "Японская кухня - роллы и суши"},
        {"name": "Напитки", "description": "Холодные и горячие напитки"},
        {"name": "Десерты", "description": "Сладкие десерты и выпечка"},
    ]
    
    categories = {}
    for cat_data in categories_data:
        category, created = Category.objects.get_or_create(
            name=cat_data["name"],
            defaults={"description": cat_data["description"]}
        )
        categories[cat_data["name"]] = category
        if created:
            print(f"✓ Создана категория: {category.name}")
    
    # Создаем продукты
    products_data = [
        {
            "name": "Маргарита",
            "description": "Классическая пицца с томатами, моцареллой и базиликом",
            "price": "15.99",
            "category": "Пицца"
        },
        {
            "name": "Пепперони",
            "description": "Пицца с пепперони, моцареллой и томатным соусом",
            "price": "18.99",
            "category": "Пицца"
        },
        {
            "name": "Четыре сыра",
            "description": "Пицца с моцареллой, пармезаном, горгонзолой и рикоттой",
            "price": "20.99",
            "category": "Пицца"
        },
        {
            "name": "Филадельфия ролл",
            "description": "Ролл с лососем, сливочным сыром и огурцом",
            "price": "12.99",
            "category": "Суши"
        },
        {
            "name": "Калифорния ролл",
            "description": "Ролл с крабом, авокадо и огурцом",
            "price": "11.99",
            "category": "Суши"
        },
        {
            "name": "Кока-Кола",
            "description": "Газированный напиток Coca-Cola 0.5л",
            "price": "2.50",
            "category": "Напитки"
        },
        {
            "name": "Кофе Американо",
            "description": "Классический кофе американо",
            "price": "3.50",
            "category": "Напитки"
        },
        {
            "name": "Тирамису",
            "description": "Итальянский десерт с кофе и маскарпоне",
            "price": "8.99",
            "category": "Десерты"
        },
        {
            "name": "Чизкейк",
            "description": "Классический чизкейк с ягодным соусом",
            "price": "7.99",
            "category": "Десерты"
        }
    ]
    
    for prod_data in products_data:
        product, created = Product.objects.get_or_create(
            name=prod_data["name"],
            defaults={
                "description": prod_data["description"],
                "price": prod_data["price"],
                "category": categories[prod_data["category"]],
                "available": True
            }
        )
        if created:
            print(f"✓ Создан продукт: {product.name} - ${product.price}")
    
    # Зоны доставки
    zones = [
        {"name": "Центр Каракола", "description": "Центральная часть города", "delivery_fee": 100, "estimated_time": 30},
        {"name": "Южный район", "description": "Южная часть города", "delivery_fee": 150, "estimated_time": 40},
        {"name": "Северный район", "description": "Северная часть города", "delivery_fee": 120, "estimated_time": 35},
    ]
    for z in zones:
        zone, created = DeliveryZone.objects.get_or_create(name=z["name"], defaults=z)
        if created:
            print(f"✓ Зона доставки: {zone.name}")
    
    # Рестораны
    restaurants = [
        {"name": "Pizza House", "address": "ул. Ленина, 1", "latitude": 42.4905, "longitude": 78.3930, "phone_number": "+996555111111"},
        {"name": "Sushi Time", "address": "ул. Абдрахманова, 15", "latitude": 42.4910, "longitude": 78.3950, "phone_number": "+996555222222"},
        {"name": "Burger King", "address": "ул. Токтогула, 50", "latitude": 42.4920, "longitude": 78.3910, "phone_number": "+996555333333"},
    ]
    for r in restaurants:
        rest, created = Restaurant.objects.get_or_create(name=r["name"], defaults=r)
        if created:
            print(f"✓ Ресторан: {rest.name}")
    
    # Курьеры
    couriers = [
        {"username": "courier1", "first_name": "Айбек", "last_name": "Усенов", "phone_number": "+996700111111", "vehicle_type": "car"},
        {"username": "courier2", "first_name": "Бакыт", "last_name": "Кадыров", "phone_number": "+996700222222", "vehicle_type": "bicycle"},
        {"username": "courier3", "first_name": "Данияр", "last_name": "Садыков", "phone_number": "+996700333333", "vehicle_type": "motorcycle"},
    ]
    for c in couriers:
        user, _ = User.objects.get_or_create(username=c["username"], defaults={"first_name": c["first_name"], "last_name": c["last_name"]})
        courier, created = DeliveryPerson.objects.get_or_create(user=user, defaults={
            "phone_number": c["phone_number"],
            "vehicle_type": c["vehicle_type"],
            "status": "available",
            "is_available": True,
            "current_latitude": 42.4907,
            "current_longitude": 78.3936,
        })
        if created:
            print(f"✓ Курьер: {user.username}")

    print("\n✅ Тестовые данные успешно созданы!")
    print(f"📊 Статистика:")
    print(f"   - Категорий: {Category.objects.count()}")
    print(f"   - Продуктов: {Product.objects.count()}")
    print(f"\n🌐 API доступен по адресам:")
    print(f"   - Категории: http://127.0.0.1:8000/api/categories/")
    print(f"   - Продукты: http://127.0.0.1:8000/api/products/")
    print(f"   - Админка: http://127.0.0.1:8000/admin/")
    print("\n✅ Тестовые зоны, рестораны и курьеры добавлены!")

if __name__ == "__main__":
    create_test_data() 