from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    estimated_time = models.IntegerField(help_text="Время доставки в минутах", default=30)
    is_active = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name

class DeliveryPerson(models.Model):
    STATUS_CHOICES = [
        ('available', 'Доступен'),
        ('busy', 'Занят'),
        ('offline', 'Не в сети'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50, choices=[
        ('bicycle', 'Велосипед'),
        ('motorcycle', 'Мотоцикл'),
        ('car', 'Автомобиль'),
        ('foot', 'Пешком'),
    ])
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    last_location_update = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_vehicle_type_display()}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтвержден'),
        ('preparing', 'Готовится'),
        ('assigned', 'Назначен курьер'),
        ('picked_up', 'Курьер забрал'),
        ('delivering', 'Доставляется'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]
    
    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, through='OrderItem')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Адрес доставки
    delivery_address = models.TextField()
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Контактная информация
    phone_number = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=100, default='Клиент')
    
    # Время
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    # Курьер
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.SET_NULL, null=True, blank=True)
    restaurant = models.ForeignKey('Restaurant', on_delete=models.SET_NULL, null=True, blank=True)
    delivery_zone = models.ForeignKey(DeliveryZone, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Дополнительная информация
    notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=20, choices=[
        ('cash', 'Наличные'),
        ('card', 'Карта'),
        ('online', 'Онлайн'),
        ('elcart', 'Элкарт'),
        ('mbank', 'МБанк'),
        ('eldik', 'Элдик'),
        ('optima', 'Optima Bank'),
        ('demir', 'Demir Bank'),
        ('bakai', 'Bakai Bank'),
        ('kompanion', 'Kompanion Bank'),
        ('rahatpay', 'Рахат Pay'),
        ('kaspi', 'Kaspi'),
        ('applepay', 'Apple Pay'),
        ('googlepay', 'Google Pay'),
    ], default='cash')
    
    service_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Комиссия сервиса")
    courier_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Оплата курьеру")
    
    def __str__(self):
        return f"Заказ {self.order_id} - {self.customer.username}"
    
    @property
    def total_with_delivery(self):
        return self.total_amount + self.delivery_fee

    def calculate_fees(self):
        # Попытка рассчитать расстояние через 2ГИС
        distance_meters = None
        try:
            from delivery.services import DGISService  # локальный импорт, чтобы избежать циклов
            if self.restaurant and self.delivery_latitude and self.delivery_longitude:
                dgis = DGISService()
                matrix = dgis.get_distance_matrix(
                    origins=[(self.restaurant.latitude, self.restaurant.longitude)],
                    destinations=[(float(self.delivery_latitude), float(self.delivery_longitude))]
                )
                distance_meters = matrix['routes'][0]['distance']  # в метрах
        except Exception:
            # Если API не доступен — fallback на фиксированный тариф
            distance_meters = None

        if distance_meters:
            from delivery.services import DGISService
            delivery_fee = DGISService().calculate_delivery_cost(distance_meters)
        else:
            # Fallback логика (как раньше)
            zone_fee = self.delivery_zone.delivery_fee if self.delivery_zone else 100
            percent_fee = self.total_amount * 0.10  # 10%
            min_fee = 80
            delivery_fee = max(zone_fee, percent_fee, min_fee)

        # 4. Комиссия сервиса (например, 15% от стоимости доставки)
        service_fee = delivery_fee * 0.15
        # 5. Оплата курьеру (остальное)
        courier_fee = delivery_fee - service_fee
        self.delivery_fee = delivery_fee
        self.service_fee = service_fee
        self.courier_fee = courier_fee
        return delivery_fee, service_fee, courier_fee

    def save(self, *args, **kwargs):
        self.calculate_fees()
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

class DeliveryTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Отслеживание {self.order.order_id} - {self.timestamp}"

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    phone_number = models.CharField(max_length=20)
    working_hours = models.CharField(max_length=100, default="09:00-22:00")
    is_active = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name

class Rating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    courier = models.ForeignKey(DeliveryPerson, on_delete=models.CASCADE, related_name='ratings')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='ratings')
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.score} for {self.order.order_id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # update aggregates
        self.update_aggregates()

    def update_aggregates(self):
        from django.db.models import Avg
        # courier average
        courier_avg = self.courier.ratings.aggregate(avg=Avg('score'))['avg'] or 0
        self.courier.avg_rating = courier_avg
        self.courier.save(update_fields=['avg_rating'])
        # restaurant average
        rest_avg = self.restaurant.ratings.aggregate(avg=Avg('score'))['avg'] or 0
        self.restaurant.avg_rating = rest_avg
        self.restaurant.save(update_fields=['avg_rating'])
