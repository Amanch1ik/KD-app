from rest_framework import serializers
from .models import Category, Product, Order, OrderItem, DeliveryPerson, DeliveryZone, DeliveryTracking, Restaurant, Rating
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


# Сериализатор для регистрации нового пользователя
class UserRegistrationSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': "Оба пароля должны совпадать."})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

# Сериализатор для входа (получения токена)
class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            if not user:
                raise serializers.ValidationError('Неверные учетные данные.', code='authorization')
        else:
            raise serializers.ValidationError('"Имя пользователя" и "пароль" обязательны.', code='authorization')

        data['user'] = user
        return data


# Сериализатор для модели User (если нужна информация о пользователе)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'category', 'category_name', 'image', 'available', 'created_at']

class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = '__all__'

class DeliveryPersonSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = DeliveryPerson
        fields = [
            'id', 'username', 'first_name', 'last_name', 'phone_number', 
            'vehicle_type', 'current_latitude', 'current_longitude', 
            'status', 'last_location_update', 'is_available'
        ]

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = '__all__'

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_price', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_username = serializers.CharField(source='customer.username', read_only=True)
    delivery_person_info = DeliveryPersonSerializer(source='delivery_person', read_only=True)
    delivery_zone_info = DeliveryZoneSerializer(source='delivery_zone', read_only=True)
    restaurant_info = RestaurantSerializer(source='restaurant', read_only=True)
    total_with_delivery = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    service_fee = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    courier_fee = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'customer', 'customer_username', 'items', 
            'total_amount', 'delivery_fee', 'service_fee', 'courier_fee', 'total_with_delivery', 'status',
            'delivery_address', 'delivery_latitude', 'delivery_longitude',
            'phone_number', 'customer_name', 'restaurant', 'notes', 'payment_method',
            'created_at', 'updated_at',
            'estimated_delivery_time', 'actual_delivery_time',
            'delivery_person', 'delivery_person_info', 'delivery_zone', 'delivery_zone_info',
            'restaurant', 'restaurant_info'
        ]

class DeliveryTrackingSerializer(serializers.ModelSerializer):
    delivery_person_name = serializers.CharField(source='delivery_person.user.username', read_only=True)
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    
    class Meta:
        model = DeliveryTracking
        fields = [
            'id', 'order', 'order_id', 'delivery_person', 'delivery_person_name',
            'latitude', 'longitude', 'timestamp', 'status', 'estimated_arrival'
        ]

# Сериализаторы для обновления местоположения
class LocationUpdateSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    status = serializers.CharField(max_length=50, required=False)

class DeliveryPersonLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPerson
        fields = ['current_latitude', 'current_longitude', 'status', 'last_location_update']

# Сериализатор для создания заказа с геолокацией
class CreateOrderSerializer(serializers.ModelSerializer):
    delivery_latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    delivery_longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    
    class Meta:
        model = Order
        fields = [
            'total_amount', 'delivery_address', 'delivery_latitude', 'delivery_longitude',
            'phone_number', 'customer_name', 'restaurant', 'notes', 'payment_method'
        ]

# Сериализатор для карты
class MapDataSerializer(serializers.Serializer):
    delivery_persons = DeliveryPersonSerializer(many=True)
    active_orders = OrderSerializer(many=True)
    restaurants = RestaurantSerializer(many=True)

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'order', 'score', 'comment', 'created_at']
