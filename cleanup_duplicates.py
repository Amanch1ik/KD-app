#!/usr/bin/env python
"""
Скрипт для удаления дубликатов категорий, ресторанов и курьеров.
Запуск: python cleanup_duplicates.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karakoldelivery.settings')
django.setup()

from delivery.models import Category, Restaurant, DeliveryPerson
from django.contrib.auth.models import User


def cleanup_model(model, field_name):
    print(f"\nПроверка дубликатов для {model.__name__}...")
    seen = set()
    deleted = 0
    for obj in model.objects.all().order_by(field_name, 'id'):
        value = getattr(obj, field_name)
        if value in seen:
            obj.delete()
            deleted += 1
        else:
            seen.add(value)
    print(f"Удалено {deleted} дубликатов из {model.__name__}")

# Категории
cleanup_model(Category, 'name')
# Рестораны
cleanup_model(Restaurant, 'name')
# Курьеры (по username пользователя)
def cleanup_couriers():
    print("\nПроверка дубликатов для DeliveryPerson...")
    seen = set()
    deleted = 0
    for courier in DeliveryPerson.objects.select_related('user').all().order_by('user__username', 'id'):
        username = courier.user.username
        if username in seen:
            courier.delete()
            deleted += 1
        else:
            seen.add(username)
    print(f"Удалено {deleted} дубликатов из DeliveryPerson")

cleanup_couriers()

print("\n✅ Очистка завершена!") 