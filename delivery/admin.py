from django.contrib import admin
from .models import Category, Product, Order, OrderItem, DeliveryPerson, DeliveryZone, DeliveryTracking, Restaurant, Rating

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']
    list_filter = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'available', 'created_at']
    list_filter = ['category', 'available', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'available']

@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'delivery_fee', 'estimated_time', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    list_editable = ['delivery_fee', 'estimated_time', 'is_active']

@admin.register(DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'vehicle_type', 'status', 'is_available', 'avg_rating', 'last_location_update']
    list_filter = ['vehicle_type', 'status', 'is_available']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone_number']
    list_editable = ['status', 'is_available']
    readonly_fields = ['last_location_update']

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone_number', 'working_hours', 'avg_rating', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'address']
    list_editable = ['is_active']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ['product', 'quantity', 'price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer', 'total_amount', 'delivery_fee', 'service_fee', 'courier_fee', 'status', 'delivery_person', 'restaurant', 'created_at']
    list_filter = ['status', 'created_at', 'payment_method']
    search_fields = ['order_id', 'customer__username', 'delivery_address', 'customer_name']
    list_editable = ['status', 'delivery_fee', 'restaurant']
    inlines = [OrderItemInline]
    readonly_fields = ['order_id', 'created_at', 'updated_at', 'estimated_delivery_time', 'actual_delivery_time']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_id', 'customer', 'status', 'total_amount', 'delivery_fee', 'service_fee', 'courier_fee')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_latitude', 'delivery_longitude', 'delivery_person', 'delivery_zone', 'restaurant')
        }),
        ('Контактная информация', {
            'fields': ('phone_number', 'customer_name')
        }),
        ('Время', {
            'fields': ('created_at', 'updated_at', 'estimated_delivery_time', 'actual_delivery_time')
        }),
        ('Дополнительно', {
            'fields': ('notes', 'payment_method')
        }),
    )

@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    list_display = ['order', 'delivery_person', 'latitude', 'longitude', 'timestamp', 'status']
    list_filter = ['timestamp', 'status']
    search_fields = ['order__order_id', 'delivery_person__user__username']
    readonly_fields = ['timestamp']

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['order', 'score', 'courier', 'restaurant', 'created_at']
    list_filter = ['score', 'created_at']
    search_fields = ['order__order_id', 'comment', 'courier__user__username', 'restaurant__name']
