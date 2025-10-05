import logging
import re

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
User = get_user_model()
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
# Removed parler_rest dependency for serializers to avoid runtime errors when Parler is not configured
from django.utils.translation import get_language
from django.core.validators import EmailValidator
from datetime import date
from .models import UserProfile

from .models import (Category, DeliveryPerson, DeliveryTracking, DeliveryZone,
                     DeviceToken, Order, OrderItem, Payment, Payout, Product,
                     Rating, Restaurant, UserProfile)
from .validators import PHONE_NUMBER_VALIDATOR # Импортируем новый валидатор

logger = logging.getLogger(__name__)


# Сериализатор для регистрации нового пользователя
class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={"input_type": "password"}, write_only=True)
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True,
        validators=[PHONE_NUMBER_VALIDATOR]
    )
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate_phone_number(self, value):
        # Удаляем все нецифровые символы для проверки уникальности
        cleaned_value = re.sub(r'\D', '', value)
        if cleaned_value and UserProfile.objects.filter(
                phone_number__icontains=cleaned_value
        ).exclude(user=self.instance).exists():
            raise serializers.ValidationError("Пользователь с таким номером телефона уже существует.")
        return value

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "phone_number"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError(
                {"password": "Оба пароля должны совпадать."}
            )

        # Валидация пароля с использованием Django валидаторов
        try:
            validate_password(
                data["password"], user=None
            )  # user=None, так как пользователь еще не создан
        except Exception as e:
            raise serializers.ValidationError({"password": str(e)})

        return data

    def create(self, validated_data):
        phone_number = validated_data.pop("phone_number", None)
        email = validated_data.pop("email", "")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=email,
            password=validated_data["password"],
        )
        if phone_number:
            # Создаем UserProfile, если его нет
            UserProfile.objects.get_or_create(
                user=user, defaults={
                    "phone_number": phone_number})
            user.profile.phone_number = phone_number
            user.profile.save()
        return user


# Сериализатор для входа (получения токена)
class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if username and password:
            user = authenticate(
                request=self.context.get("request"),
                username=username,
                password=password,
            )
            if not user:
                raise serializers.ValidationError(
                    "Неверные учетные данные.", code="authorization"
                )
        else:
            raise serializers.ValidationError(
                '"Имя пользователя" и "пароль" обязательны.', code="authorization"
            )

        data["user"] = user
        return data


# Сериализатор для модели User (если нужна информация о пользователе)
class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[EmailValidator()],
        required=False,
        allow_blank=True,
        allow_null=True
    )
    
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True
    )
    
    preferred_language = serializers.ChoiceField(
        choices=UserProfile.LANGUAGE_CHOICES,
        required=False
    )
    
    notification_settings = serializers.MultipleChoiceField(
        choices=UserProfile.NOTIFICATION_CHOICES,
        required=False
    )
    
    phone_number = serializers.CharField(
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$', 
                message="Номер телефона должен быть в международном формате, например +996555123456"
            )
        ],
        required=False,
        allow_blank=True,
        allow_null=True
    )

    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'role', 'email', 'date_of_birth', 
            'preferred_language', 'notification_settings', 
            'phone_number', 'address', 'profile_picture',
            'social_links', 'payment_methods', 'order_preferences'
        ]
    
    def validate_date_of_birth(self, value):
        """
        Проверка даты рождения
        """
        if value:
            # Проверяем, что дата рождения не в будущем
            if value > date.today():
                raise serializers.ValidationError("Дата рождения не может быть в будущем")
            
            # Проверяем возраст (например, не младше 14 лет)
            age = (date.today() - value).days / 365.25
            if age < 14:
                raise serializers.ValidationError("Минимальный возраст - 14 лет")
        
        return value
    
    def validate_social_links(self, value):
        """
        Проверка социальных ссылок
        """
        if value:
            # Пример проверки формата ссылок
            valid_domains = ['facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com']
            for link in value:
                if not any(domain in link for domain in valid_domains):
                    raise serializers.ValidationError(f"Неподдерживаемая социальная сеть в ссылке: {link}")
        
        return value
    
    def validate(self, data):
        """
        Дополнительная валидация данных профиля
        """
        # Проверка уникальности email, если он указан
        if 'email' in data and data['email']:
            existing_profile = UserProfile.objects.filter(email=data['email']).exclude(pk=self.instance.pk if self.instance else None)
            if existing_profile.exists():
                raise serializers.ValidationError({"email": "Этот email уже используется другим пользователем"})
        
        return data


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(
        read_only=False
    )  # profile теперь может быть обновлен
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile"]
        read_only_fields = [
            "username",
            "email",
        ]  # username и email не меняем через этот сериализатор

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save()

        # Обновляем поля UserProfile
        if profile_data and hasattr(instance, "profile"):
            profile_serializer = self.fields["profile"]
            profile_instance = instance.profile
            # Проверяем, есть ли изображение профиля в profile_data
            if "profile_picture" in profile_data:
                profile_instance.profile_picture = profile_data.pop("profile_picture")
                profile_instance.save(update_fields=["profile_picture"])
            logger.debug(f"Profile data for update: {profile_data}")
            profile_serializer = UserProfileSerializer(
                instance=profile_instance, data=profile_data, partial=True
            )
            if profile_serializer.is_valid(raise_exception=True):
                profile_serializer.save()

        return instance


class CategorySerializer(serializers.ModelSerializer):
    """Simple Category serializer without Parler dependency.
    Adds a `translations` object in representation using model fields as fallback.
    """
    class Meta:
        model = Category
        fields = ['id', 'is_active', 'name', 'description']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        current_language = get_language()
        rep['translations'] = {
            current_language: {
                'name': instance.name,
                'description': instance.description or ''
            }
        }
        return rep

class RestaurantSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id',
            'is_active',
            'avg_rating',
            'products',
            'latitude',
            'longitude',
            'name',
            'description'
        ]

    def get_products(self, obj):
        products = obj.products.filter(is_available=True)
        # Use `.values()` for a lightweight representation when possible to
        # avoid N+1 queries when serializing large product lists. Fall back to
        # full serializer for   complex cases.
        try:
            return ProductSerializer(products.select_related('category', 'restaurant'), many=True).data
        except Exception:
            return ProductSerializer(products, many=True).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        current_language = get_language()
        rep['translations'] = {
            current_language: {
                'name': instance.name,
                'description': instance.description or ''
            }
        }
        return rep

class ProductSerializer(serializers.ModelSerializer):
    restaurant = RestaurantSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'restaurant',
            'category',
            'is_available'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        current_language = get_language()
        rep['translations'] = {
            current_language: {
                'name': instance.name,
                'description': instance.description or ''
            }
        }
        return rep

class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = "__all__"


class DeliveryPersonSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = DeliveryPerson
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "vehicle_type",
            "current_latitude",
            "current_longitude",
            "status",
            "last_location_update",
            "is_available",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "product_price", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для заказов с локализацией статусов
    """
    status_display = serializers.SerializerMethodField()
    payment_method_display = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 
            'customer', 
            'restaurant', 
            'status', 
            'status_display',
            'payment_method', 
            'payment_method_display',
            'delivery_address', 
            'phone_number'
        ]

    def get_status_display(self, obj):
        """
        Получение локализованного статуса
        """
        return _(dict(Order.STATUS_CHOICES).get(obj.status, obj.status))

    def get_payment_method_display(self, obj):
        """
        Получение локализованного способа оплаты
        """
        return _(dict(Order.PAYMENT_METHODS).get(obj.payment_method, obj.payment_method))


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    delivery_person_name = serializers.CharField(
        source="delivery_person.user.username",
        read_only=True,
    )
    order_id = serializers.IntegerField(source="order.id", read_only=True)

    class Meta:
        model = DeliveryTracking
        fields = [
            "id",
            "order",
            "order_id",
            "delivery_person",
            "delivery_person_name",
            "latitude",
            "longitude",
            "timestamp",
            "status",
            "estimated_arrival",
        ]


# Сериализаторы для обновления местоположения
class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    status = serializers.CharField(max_length=50, required=False)


class DeliveryPersonLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPerson
        fields = [
            "current_latitude",
            "current_longitude",
            "status",
            "last_location_update",
        ]


# Сериализатор для создания заказа с геолокацией
class CreateOrderSerializer(serializers.ModelSerializer):
    delivery_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
    )
    delivery_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
    )

    class Meta:
        model = Order
        fields = [
            "total_amount",
            "delivery_address",
            "delivery_latitude",
            "delivery_longitude",
            "phone_number",
            "customer_name",
            "restaurant",
            "notes",
            "payment_method",
        ]


# Сериализатор для карты
class MapDataSerializer(serializers.Serializer):
    delivery_persons = DeliveryPersonSerializer(many=True)
    active_orders = OrderSerializer(many=True)
    restaurants = RestaurantSerializer(many=True)


class RatingSerializer(serializers.ModelSerializer):
    courier = serializers.CharField(source="courier.user.username", read_only=True)
    restaurant = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Rating
        fields = [
            "id",
            "order",
            "courier",
            "restaurant",
            "score",
            "comment",
            "created_at",
        ]


class DeliveryPersonDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPerson
        fields = [
            "document_type",
            "document_number",
            "document_front_image",
            "document_back_image",
            "is_documents_verified",
        ]
        read_only_fields = [
            "is_documents_verified",
        ]  # Это поле должно обновляться админом


class PayoutSerializer(serializers.ModelSerializer):
    delivery_person_username = serializers.CharField(
        source="delivery_person.user.username",
        read_only=True,
    )

    class Meta:
        model = Payout
        fields = [
            "id",
            "delivery_person",
            "delivery_person_username",
            "amount",
            "payout_date",
            "description",
        ]
        read_only_fields = [
            "delivery_person",
            "payout_date",
        ]  # Эти поля должны устанавливаться на бэкенде


class PaymentSerializer(serializers.ModelSerializer):
    payment_method = serializers.ChoiceField(choices=Order.payment_method.field.choices)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "amount",
            "payment_method",
            "transaction_id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "created_at",
            "updated_at",
        ]  # Статус и даты обновляются автоматически


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["id", "user", "registration_id", "device_type", "created_at"]
        read_only_fields = ["user", "created_at"]


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for initiating password reset
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        """
        Validate email format
        """
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset
    """
    token = serializers.CharField(
        max_length=128, 
        required=True, 
        error_messages={
            'blank': 'Reset token is required.',
            'max_length': 'Invalid reset token.'
        }
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        """
        Validate password reset data
        """
        # Check if passwords match
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })

        # Validate password strength
        try:
            validate_password(data['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })

        return data

    def validate_token(self, value):
        """
        Validate token format
        """
        if not value:
            raise serializers.ValidationError("Reset token is required.")
        return value
