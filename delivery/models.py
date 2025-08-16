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

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('client', 'Клиент'),
        ('courier', 'Курьер'),
        ('admin', 'Админ'),
        ('restaurant_partner', 'Партнёр-магазин'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


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

    # Поля для верификации документов
    document_type = models.CharField(max_length=50, blank=True, null=True, help_text="Тип документа (паспорт, права и т.д.)")
    document_number = models.CharField(max_length=100, blank=True, null=True, help_text="Номер документа")
    document_front_image = models.ImageField(upload_to='documents/front/', blank=True, null=True, help_text="Изображение лицевой стороны документа")
    document_back_image = models.ImageField(upload_to='documents/back/', blank=True, null=True, help_text="Изображение обратной стороны документа")
    is_documents_verified = models.BooleanField(default=False, help_text="Статус верификации документов")
    document_submission_date = models.DateTimeField(auto_now_add=True, null=True, blank=True, help_text="Дата подачи документов")
    
    def __str__(self):
        return f"{self.user.username} - {self.get_vehicle_type_display()}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('cart', 'Корзина'), # Добавлен статус 'Корзина'
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
    partner_user = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_restaurants', help_text="Пользователь, управляющий этим рестораном (партнёр-магазин)")

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

class Payout(models.Model):
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Выплата {self.amount} для {self.delivery_person.user.username} от {self.payout_date.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['payout_date']

class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Процентная скидка'),
        ('fixed_amount', 'Фиксированная сумма'),
        ('free_delivery', 'Бесплатная доставка'),
    ]
    code = models.CharField(max_length=50, unique=True, help_text="Промокод (например, NEWYEAR2024)")
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='fixed_amount')
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, help_text="Значение скидки (например, 10 для 10% или 150 для 150 ед.)")
    start_date = models.DateTimeField(help_text="Дата начала действия промокода")
    end_date = models.DateTimeField(help_text="Дата окончания действия промокода")
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Минимальная сумма заказа для применения промокода")
    is_active = models.BooleanField(default=True, help_text="Активен ли промокод")
    usage_limit = models.PositiveIntegerField(blank=True, null=True, help_text="Максимальное количество использований промокода")
    times_used = models.PositiveIntegerField(default=0, help_text="Сколько раз промокод был использован")

    def __str__(self):
        return self.code

    def is_valid(self, order_amount):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date > now or self.end_date < now:
            return False
        if order_amount < self.min_order_amount:
            return False
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            return False
        return True

    def apply_discount(self, order_amount, delivery_fee):
        if not self.is_valid(order_amount):
            return 0, delivery_fee, False # Скидка, новая стоимость доставки, флаг применения

        if self.discount_type == 'percentage':
            discount_amount = order_amount * (self.discount_value / 100)
            return discount_amount, delivery_fee, True
        elif self.discount_type == 'fixed_amount':
            discount_amount = self.discount_value
            return discount_amount, delivery_fee, True
        elif self.discount_type == 'free_delivery':
            return 0, 0, True # 0 скидка, 0 доставка
        return 0, delivery_fee, False


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('completed', 'Завершена'),
        ('failed', 'Неуспешна'),
        ('refunded', 'Возвращена'),
    ]
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Order {self.order.order_id} - {self.amount} ({self.status})"


class DeviceToken(models.Model):
    DEVICE_TYPE_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    registration_id = models.CharField(max_length=255, unique=True, help_text="Токен устройства для push-уведомлений")
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.username} ({self.device_type})"
