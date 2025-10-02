from django.contrib import admin
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.admin import UserAdmin
from .models import (
    Category, DeliveryPerson, DeliveryTracking, DeliveryZone,
    Order, OrderItem, Payment, Product, Restaurant, 
    UserProfile, DeviceToken, PromoCode
)

# Регистрация моделей без перевода
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'email', 'preferred_language']
    list_filter = ['role', 'preferred_language']
    search_fields = ['user__username', 'email']

# Остальные регистрации моделей без перевода
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ['user', 'avg_rating']

# Добавьте остальные регистрации моделей здесь
