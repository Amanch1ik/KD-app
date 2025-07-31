from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.utils import timezone
from datetime import timedelta
from .models import Category, Product, Order, OrderItem, DeliveryPerson, DeliveryZone, DeliveryTracking, Restaurant, Rating
from .serializers import (
    CategorySerializer, ProductSerializer, OrderSerializer, OrderItemSerializer,
    DeliveryPersonSerializer, DeliveryZoneSerializer, DeliveryTrackingSerializer,
    RestaurantSerializer, LocationUpdateSerializer, DeliveryPersonLocationSerializer,
    CreateOrderSerializer, MapDataSerializer, RatingSerializer,
    UserSerializer, UserRegistrationSerializer, AuthTokenSerializer
)
from .utils import broadcast_map_update
from django.contrib.auth.models import User
from rest_framework.views import APIView
from django.urls import reverse
from rest_framework.reverse import reverse as drf_reverse
from rest_framework.authtoken.models import Token

# Create your views here.

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if category_id:
            products = Product.objects.filter(category_id=category_id, available=True)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'category_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

class DeliveryZoneViewSet(viewsets.ModelViewSet):
    queryset = DeliveryZone.objects.filter(is_active=True)
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class DeliveryPersonViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPerson.objects.all()
    serializer_class = DeliveryPersonSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def update_location(self, request, pk=None):
        delivery_person = self.get_object()
        serializer = LocationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            delivery_person.current_latitude = serializer.validated_data['latitude']
            delivery_person.current_longitude = serializer.validated_data['longitude']
            if 'status' in serializer.validated_data:
                delivery_person.status = serializer.validated_data['status']
            delivery_person.save()
            
            # Создаем запись отслеживания для активных заказов
            active_orders = Order.objects.filter(
                delivery_person=delivery_person,
                status__in=['assigned', 'picked_up', 'delivering']
            )
            
            for order in active_orders:
                DeliveryTracking.objects.create(
                    order=order,
                    delivery_person=delivery_person,
                    latitude=delivery_person.current_latitude,
                    longitude=delivery_person.current_longitude,
                    status=delivery_person.status
                )
            
            broadcast_map_update()
            return Response({'status': 'Location updated successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        available_persons = DeliveryPerson.objects.filter(
            is_available=True,
            status='available'
        )
        serializer = self.get_serializer(available_persons, many=True)
        return Response(serializer.data)

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(customer=self.request.user)
    
    def perform_create(self, serializer):
        # Автоматически назначаем курьера при создании заказа
        order = serializer.save(customer=self.request.user)
        
        # Находим ближайшего доступного курьера
        available_person = DeliveryPerson.objects.filter(
            is_available=True,
            status='available'
        ).first()
        
        if available_person:
            order.delivery_person = available_person
            order.status = 'assigned'
            # помечаем курьера занятым
            available_person.status = 'busy'
            available_person.is_available = False
            available_person.save()
            
            # Рассчитываем примерное время доставки
            order.estimated_delivery_time = timezone.now() + timedelta(minutes=30)
            order.save()
        
        # Если клиент передал restaurant_id, сохраняем
        restaurant_id = self.request.data.get('restaurant')
        if restaurant_id:
            try:
                order.restaurant = Restaurant.objects.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                pass
    
    @action(detail=True, methods=['post'])
    def assign_courier(self, request, pk=None):
        order = self.get_object()
        courier_id = request.data.get('courier_id')
        
        try:
            courier = DeliveryPerson.objects.get(id=courier_id, is_available=True)
            # Освобождаем предыдущего курьера (если был)
            if order.delivery_person and order.delivery_person != courier:
                prev = order.delivery_person
                prev.status = 'available'
                prev.is_available = True
                prev.save()

            # Назначаем нового
            order.delivery_person = courier
            order.status = 'assigned'
            order.save()

            # Обновляем статус курьера
            courier.status = 'busy'
            courier.is_available = False
            courier.save()

            broadcast_map_update()
            return Response({'status': 'Courier assigned successfully'})
        except DeliveryPerson.DoesNotExist:
            return Response({'error': 'Courier not found or not available'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            if new_status in ['delivered', 'cancelled']:
                order.actual_delivery_time = timezone.now()
                # освобождаем курьера
                if order.delivery_person:
                    dp = order.delivery_person
                    dp.status = 'available'
                    dp.is_available = True
                    dp.save()
            order.save()
            broadcast_map_update()
            return Response({'status': 'Order status updated successfully'})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Клиент оценивает доставку (1-5)"""
        order = self.get_object()
        if order.customer != request.user:
            return Response({'error': 'Можно оценивать только свои заказы'}, status=403)
        if order.status != 'delivered':
            return Response({'error': 'Оценка доступна только для доставленных заказов'}, status=400)
        if hasattr(order, 'rating'):
            return Response({'error': 'Заказ уже оценён'}, status=400)

        score = int(request.data.get('score', 0))
        comment = request.data.get('comment', '')
        if score < 1 or score > 5:
            return Response({'error': 'Оценка от 1 до 5'}, status=400)

        rating = Rating.objects.create(
            order=order,
            courier=order.delivery_person,
            restaurant=order.restaurant,
            score=score,
            comment=comment
        )
        broadcast_map_update()
        return Response(RatingSerializer(rating).data, status=201)
    
    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        order = self.get_object()
        tracking_data = DeliveryTracking.objects.filter(order=order).order_by('-timestamp')
        serializer = DeliveryTrackingSerializer(tracking_data, many=True)
        return Response(serializer.data)

class DeliveryTrackingViewSet(viewsets.ModelViewSet):
    queryset = DeliveryTracking.objects.all()
    serializer_class = DeliveryTrackingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return DeliveryTracking.objects.all()
        return DeliveryTracking.objects.filter(order__customer=self.request.user)

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

# Специальное представление для карты
class MapViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def data(self, request):
        """Получить все данные для отображения на карте"""
        delivery_persons = DeliveryPerson.objects.filter(is_available=True)
        active_orders = Order.objects.filter(
            status__in=['assigned', 'picked_up', 'delivering']
        )
        restaurants = Restaurant.objects.filter(is_active=True)
        
        data = {
            'delivery_persons': DeliveryPersonSerializer(delivery_persons, many=True).data,
            'active_orders': OrderSerializer(active_orders, many=True).data,
            'restaurants': RestaurantSerializer(restaurants, many=True).data,
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def delivery_persons(self, request):
        """Получить только курьеров для карты"""
        delivery_persons = DeliveryPerson.objects.filter(is_available=True)
        serializer = DeliveryPersonSerializer(delivery_persons, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active_orders(self, request):
        """Получить только активные заказы для карты"""
        active_orders = Order.objects.filter(
            status__in=['assigned', 'picked_up', 'delivering']
        )
        serializer = OrderSerializer(active_orders, many=True)
        return Response(serializer.data)

# Custom API Root View
class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'categories': drf_reverse('category-list', request=request, format=format),
            'products': drf_reverse('product-list', request=request, format=format),
            'orders': drf_reverse('order-list', request=request, format=format),
            'delivery-zones': drf_reverse('deliveryzone-list', request=request, format=format),
            'delivery-persons': drf_reverse('deliveryperson-list', request=request, format=format),
            'restaurants': drf_reverse('restaurant-list', request=request, format=format),
            'delivery-tracking': drf_reverse('deliverytracking-list', request=request, format=format),
            'order-items': drf_reverse('orderitem-list', request=request, format=format), # Добавлено
            'ratings': drf_reverse('rating-list', request=request, format=format),       # Добавлено
            'map': drf_reverse('map-data', request=request, format=format), # Изменено с map-list на map-data
            'register': drf_reverse('register', request=request, format=format),
            'login': drf_reverse('login', request=request, format=format),
            'user-profile': drf_reverse('user-profile', request=request, format=format),
        })


# API для регистрации пользователя
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)

# API для входа пользователя (получение токена)
class LoginView(generics.CreateAPIView):
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        })

# API для получения информации о текущем пользователе
class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


def home(request):
    return render(request, 'delivery/home.html')

def map_view(request):
    """Представление для страницы с картой"""
    return render(request, 'delivery/map.html')
