import logging
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Index, Q
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
    EmailValidator,
    FileExtensionValidator
)
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import JSONField
from datetime import date
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# Базовая модель с общими методами
class BaseModel(models.Model):
    """
    Абстрактная базовая модель с общими полями
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True

class Category(BaseModel):
    """
    Категории с поддержкой перевода
    """
    name = models.CharField(
        max_length=100, 
        unique=True
    )
    description = models.TextField(
        blank=True, 
        null=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

class Restaurant(BaseModel):
    """
    Рестораны с поддержкой перевода
    """
    name = models.CharField(
        max_length=200
    )
    description = models.TextField(
        blank=True, 
        null=True
    )
    partner_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='restaurant_partner'
    )
    avg_rating = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(5.0)
        ]
    )
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Restaurant')
        verbose_name_plural = _('Restaurants')

class Product(models.Model):
    """
    Продукты с поддержкой перевода
    """
    name = models.CharField(
        max_length=200
    )
    description = models.TextField(
        blank=True, 
        null=True
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    restaurant = models.ForeignKey(
        'Restaurant', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products'
    )
    category = models.ForeignKey(
        'Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products'
    )
    is_available = models.BooleanField(
        default=True, 
        db_index=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')

class Order(models.Model):
    """
    Заказы с локализованными статусами
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('confirmed', _('Confirmed')),
        ('preparing', _('Preparing')),
        ('out_for_delivery', _('Out for Delivery')),
        ('delivered', _('Delivered')),
        ('cancelled', _('Cancelled'))
    ]

    PAYMENT_METHODS = [
        ('cash', _('Cash')),
        ('card', _('Card')),
        ('online', _('Online Payment'))
    ]

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    restaurant = models.ForeignKey(
        'Restaurant', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS,
        db_index=True
    )
    delivery_address = models.TextField()
    phone_number = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$', 
                message=_("Phone number must be entered in the format: '+999999999'.")
            )
        ]
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    courier_fee = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=0
    )
    service_fee = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=0
    )
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{_('Order')} {self.id} - {self.get_status_display()}"

    class Meta:
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        ordering = ['-created_at']

    def clean(self):
        """
        Custom validation method for Order model
        Ensures order integrity and business rules
        """
        # Validate total amount is greater than zero
        if self.total_amount <= 0:
            raise ValidationError(_("Total amount must be greater than zero"))
        
        # Ensure delivery address is not empty
        if not self.delivery_address or len(self.delivery_address.strip()) == 0:
            raise ValidationError(_("Delivery address cannot be empty"))
        
        # Validate phone number format
        phone_validator = RegexValidator(
            regex=r'^\+?1?\d{9,15}$', 
            message=_("Phone number must be entered in the format: '+999999999'.")
        )
        try:
            phone_validator(self.phone_number)
        except ValidationError as e:
            raise ValidationError({"phone_number": e.message})
        
        # Validate courier and service fees are non-negative
        if self.courier_fee < 0 or self.service_fee < 0:
            raise ValidationError(_("Courier and service fees must be non-negative"))
        
        # Ensure order status is valid
        valid_statuses = [status[0] for status in self.STATUS_CHOICES]
        if self.status not in valid_statuses:
            raise ValidationError(_("Invalid order status"))
        
        # Validate payment method
        valid_payment_methods = [method[0] for method in self.PAYMENT_METHODS]
        if self.payment_method not in valid_payment_methods:
            raise ValidationError(_("Invalid payment method"))

    def save(self, *args, **kwargs):
        """
        Override save method to perform validation before saving
        """
        self.full_clean()
        super().save(*args, **kwargs)


class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    estimated_time = models.IntegerField(
        help_text="Время доставки в минутах",
        default=30,
    )
    is_active = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("client", "Клиент"),
        ("courier", "Курьер"),
        ("admin", "Администратор"),
        ("restaurant_partner", "Партнёр-ресторан"),
    ]

    LANGUAGE_CHOICES = [
        ('ru', 'Русский'),
        ('ky', 'Кыргызский'),
        ('en', 'Английский')
    ]

    NOTIFICATION_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push-уведомления'),
        ('none', 'Не уведомлять')
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="client")
    
    # Новые поля с валидацией
    email = models.EmailField(
        blank=True, 
        null=True, 
        unique=True, 
        validators=[EmailValidator()]
    )
    
    def validate_date_of_birth(value):
        """
        Валидатор даты рождения
        """
        if value and value > date.today():
            raise ValidationError("Дата рождения не может быть в будущем")
        
        # Проверка возраста (не младше 14 лет)
        age = (date.today() - value).days / 365.25
        if age < 14:
            raise ValidationError("Минимальный возраст - 14 лет")
    
    date_of_birth = models.DateField(
        blank=True, 
        null=True, 
        validators=[validate_date_of_birth]
    )
    
    preferred_language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='ru'
    )
    
    notification_settings = models.JSONField(
        blank=True,
        null=True,
        default=list
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Номер телефона должен быть в международном формате, например +996555123456"
            )
        ]
    )
 
    address = models.TextField(blank=True, null=True)
 
    def validate_social_links(value):
        """
        Валидатор социальных ссылок
        """
        valid_domains = ['facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com']
        for link in value:
            if not any(domain in link for domain in valid_domains):
                raise ValidationError(f"Неподдерживаемая социальная сеть в ссылке: {link}")
    
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True,
        validators=[
            # Валидация размера изображения (например, не более 5 МБ)
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif'],
                message="Разрешены только изображения в форматах jpg, jpeg, png, gif"
            )
        ]
    )
    
    social_links = models.JSONField(
        blank=True,
        null=True,
        default=list,
        validators=[validate_social_links]
    )
    
    payment_methods = models.JSONField(
        blank=True,
        null=True,
        default=list
    )
    
    order_preferences = models.JSONField(
        blank=True,
        null=True,
        default=dict
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        unique_together = ['user', 'email']


class DeliveryPerson(models.Model):
    STATUS_CHOICES = [
        ("available", "Доступен"),
        ("busy", "Занят"),
        ("offline", "Не в сети"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_type = models.CharField(
        max_length=50,
        choices=(
            ("bicycle", "Велосипед"),
            ("motorcycle", "Мотоцикл"),
            ("car", "Автомобиль"),
            ("foot", "Пешком"),
        ),
    )
    current_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    current_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="offline")
    last_location_update = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    # Поля для верификации документов
    document_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Тип документа (паспорт, права и т.д.)",
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Номер документа",
    )
    document_front_image = models.ImageField(
        upload_to="documents/front/",
        blank=True,
        null=True,
        help_text="Изображение лицевой стороны документа",
    )
    document_back_image = models.ImageField(
        upload_to="documents/back/",
        blank=True,
        null=True,
        help_text="Изображение обратной стороны документа",
    )
    is_documents_verified = models.BooleanField(
        default=False,
        help_text="Статус верификации документов",
    )
    document_submission_date = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
        help_text="Дата подачи документов",
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_vehicle_type_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
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
        ordering = ["-timestamp"]

    def __str__(self):
        # Order использует поле `id`, а не `order_id`
        return f"Отслеживание {self.order.id} - " f"{self.timestamp}"


class Rating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    courier = models.ForeignKey(
        DeliveryPerson,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.score} for {self.order.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class Payout(models.Model):
    """
    Модель для выплат курьерам
    """
    PAYOUT_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processed', _('Processed')),
        ('failed', _('Failed'))
    ]

    delivery_person = models.ForeignKey(
        'DeliveryPerson', 
        on_delete=models.CASCADE, 
        related_name='payouts'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20, 
        choices=PAYOUT_STATUS_CHOICES, 
        default='pending'
    )
    created_at = models.DateTimeField(
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    transaction_details = models.TextField(
        blank=True, 
        null=True
    )

    def __str__(self):
        return f"{_('Payout')} - {self.delivery_person.user.username} - {self.amount}"

    class Meta:
        verbose_name = _('Payout')
        verbose_name_plural = _('Payouts')
        ordering = ['-created_at']


class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Процентная скидка"),
        ("fixed_amount", "Фиксированная сумма"),
        ("free_delivery", "Бесплатная доставка"),
    ]
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Промокод (например, NEWYEAR2024)",
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        default="fixed_amount",
    )
    discount_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Значение скидки (например, 10 для 10% или 150 для 150 ед.)",
    )
    start_date = models.DateTimeField(help_text="Дата начала действия промокода")
    end_date = models.DateTimeField(help_text="Дата окончания действия промокода")
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Минимальная сумма заказа для применения промокода",
    )
    is_active = models.BooleanField(default=True, help_text="Активен ли промокод")
    usage_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Максимальное количество использований промокода",
    )
    times_used = models.PositiveIntegerField(
        default=0,
        help_text="Сколько раз промокод был использован",
    )

    def __str__(self):
        return self.code

    def is_valid(self, order_amount):
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
            # Скидка, новая стоимость доставки, флаг применения
            return 0, delivery_fee, False

        if self.discount_type == "percentage":
            discount_amount = order_amount * (self.discount_value / 100)
            return discount_amount, delivery_fee, True
        elif self.discount_type == "fixed_amount":
            discount_amount = self.discount_value
            return discount_amount, delivery_fee, True
        elif self.discount_type == "free_delivery":  # 0 скидка, 0 доставка
            return 0, 0, True
        return 0, delivery_fee, False


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("completed", "Завершена"),
        ("failed", "Неуспешна"),
        ("refunded", "Возвращена"),
    ]
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"Payment for Order {self.order.id} - "
            f"{self.amount} ({self.status})"
        )


class DeviceToken(models.Model):
    DEVICE_TYPE_CHOICES = [
        ("android", "Android"),
        ("ios", "iOS"),
        ("web", "Web"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
    )
    registration_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Токен устройства для push-уведомлений",
    )
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.username} (" f"{self.device_type})"


class PasswordResetToken(models.Model):
    """
    Model to manage secure password reset tokens
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )
    token = models.CharField(
        max_length=128,
        unique=True,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        """
        Check if the token is still valid
        """
        return self.expires_at > timezone.now()

    def __str__(self):
        return f"Password Reset Token for {self.user.email}"

    class Meta:
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'token', 'expires_at'])
        ]

# Улучшенная модель пользователя
class CustomUser(AbstractUser):
    # Оптимизация полей
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True)
    preferred_language = models.CharField(
        _('preferred language'), 
        max_length=10, 
        choices=[
            ('ru', _('Russian')),
            ('ky', _('Kyrgyz')),
            ('en', _('English'))
        ], 
        default='ru',
        db_index=True
    )
    
    # Использование более эффективных полей
    notification_settings = models.JSONField(
        _('notification settings'), 
        default=dict, 
        blank=True
    )
    profile_picture = models.ImageField(
        _('profile picture'), 
        upload_to='profile_pictures/', 
        null=True, 
        blank=True
    )
    
    # Добавление индексов для часто используемых полей
    class Meta:
        indexes = [
            models.Index(fields=['email', 'is_active']),
            models.Index(fields=['preferred_language'])
        ]

    def __str__(self):
        return self.username or self.email
