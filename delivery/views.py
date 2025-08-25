from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.utils import timezone
from datetime import timedelta
from .models import Category, Product, Order, OrderItem, DeliveryPerson, DeliveryZone, DeliveryTracking, Restaurant, Rating, Payout, Payment, DeviceToken # Добавлен Payment и DeviceToken
from .serializers import (
    CategorySerializer, ProductSerializer, OrderSerializer, OrderItemSerializer,
    DeliveryPersonSerializer, DeliveryZoneSerializer, DeliveryTrackingSerializer,
    RestaurantSerializer, LocationUpdateSerializer, DeliveryPersonLocationSerializer,
    MapDataSerializer, RatingSerializer,
    UserSerializer, UserRegistrationSerializer, AuthTokenSerializer, PayoutSerializer, PaymentSerializer, DeviceTokenSerializer # Добавлен PaymentSerializer и DeviceTokenSerializer
)
from .utils import broadcast_map_update
from django.contrib.auth.models import User
from rest_framework.views import APIView
from django.urls import reverse
from rest_framework.reverse import reverse as drf_reverse
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .serializers import DeliveryPersonDocumentSerializer
from .services import DGISService # Исправленный импорт DGISService
from django.db import models
from .utils import send_push_notification # Добавлен send_push_notification

# Create your views here.

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ['name', 'description'] # Добавляем поиск по имени и описанию
    
    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get('restaurant')
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        category_id = request.query_params.get('category_id')
        if category_id:
            products = Product.objects.filter(category_id=category_id, available=True)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'category_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_restaurant(self, request):
        restaurant_id = request.query_params.get('restaurant')
        if restaurant_id:
            products = Product.objects.filter(restaurant_id=restaurant_id, available=True)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'restaurant parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=True, methods=['patch', 'put'])
    def upload_documents(self, request, pk=None):
        delivery_person = self.get_object()
        # Проверяем, что запрос делает сам курьер или администратор
        if request.user != delivery_person.user and not request.user.is_staff:
            return Response({'error': 'У вас нет прав для выполнения этого действия.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DeliveryPersonDocumentSerializer(delivery_person, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def get_balance(self, request, pk=None):
        delivery_person = self.get_object()
        if request.user != delivery_person.user and not request.user.is_staff:
            return Response({'error': 'У вас нет прав для просмотра этого баланса.'}, status=status.HTTP_403_FORBIDDEN)

        # Сумма всех заработанных комиссий курьера
        total_earned = Order.objects.filter(delivery_person=delivery_person, status='delivered').aggregate(total=models.Sum('courier_fee'))['total'] or 0
        
        # Сумма всех выплат курьеру
        total_paid = Payout.objects.filter(delivery_person=delivery_person).aggregate(total=models.Sum('amount'))['total'] or 0

        current_balance = total_earned - total_paid

        return Response({
            'delivery_person_id': delivery_person.id,
            'total_earned': total_earned,
            'total_paid': total_paid,
            'current_balance': current_balance
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def get_stats(self, request, pk=None):
        delivery_person = self.get_object()
        if request.user != delivery_person.user and not request.user.is_staff:
            return Response({'error': 'У вас нет прав для просмотра статистики.'}, status=status.HTTP_403_FORBIDDEN)

        completed_orders_count = Order.objects.filter(delivery_person=delivery_person, status='delivered').count()
        total_delivery_fee_earned = Order.objects.filter(delivery_person=delivery_person, status='delivered').aggregate(total=models.Sum('courier_fee'))['total'] or 0

        return Response({
            'delivery_person_id': delivery_person.id,
            'completed_orders_count': completed_orders_count,
            'total_delivery_fee_earned': total_delivery_fee_earned
        }, status=status.HTTP_200_OK)

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ['name', 'address'] # Добавляем поиск по имени и адресу
    # filterset_fields = ['is_active', 'avg_rating'] # Убираем django-filter

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    # filterset_fields = ['status', 'delivery_person', 'customer', 'created_at'] # Убираем django-filter
    search_fields = ['order_id', 'delivery_address', 'customer_name', 'phone_number'] # Добавляем поля для поиска
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        
        # Проверяем, является ли пользователь курьером
        if hasattr(user, 'deliveryperson'):
            courier = user.deliveryperson
            # Курьер видит свои заказы и доступные (неназначенные)
            return Order.objects.filter(models.Q(delivery_person=courier) | models.Q(status__in=['pending', 'confirmed', 'preparing'], delivery_person__isnull=True)).distinct()
        
        # Клиент видит только свои заказы
        return Order.objects.filter(customer=user)
    
    def perform_create(self, serializer):
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
            
            # Отправляем push-уведомление курьеру
            send_push_notification(
                user_or_tokens=available_person.user, 
                title="Новый заказ!", 
                message=f"Вам назначен новый заказ #{order.order_id} на сумму {order.total_with_delivery} сом."
            )
        
        # Если клиент передал restaurant_id, сохраняем
        # restaurant_id теперь должен быть внутри validated_data из OrderSerializer
        # Если фронтенд отправляет restaurant_id в корне запроса, то это нужно будет откорректировать
        # Если restaurant_id приходит внутри items_data (через product->restaurant), то тут ничего не надо
        # Для текущего фронтенда, он должен быть в root level. Проверяем.
        # Фронтенд не отправляет restaurant_id при создании заказа, он формирует OrderItems. 
        # restaurant_info должен браться из OrderItem.product.restaurant
        
        # Проверяем, есть ли restaurant_id в validated_data (этот кусок кода уже не нужен)
        # restaurant_id = self.request.data.get('restaurant')
        # if restaurant_id:
        #     try:
        #         order.restaurant = Restaurant.objects.get(id=restaurant_id)
        #     except Restaurant.DoesNotExist:
        #         pass
        
        # Добавляем ресторан к заказу из первого элемента, если он есть
        if not order.restaurant and order.items.exists():
            first_item_product_restaurant = order.items.first().product.restaurant
            if first_item_product_restaurant:
                order.restaurant = first_item_product_restaurant
                order.save()
    
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
            # Отправляем push-уведомление курьеру
            send_push_notification(
                user_or_tokens=courier.user, 
                title="Заказ назначен!", 
                message=f"Вам назначен заказ #{order.order_id} на сумму {order.total_with_delivery} сом."
            )
            return Response({'status': 'Courier assigned successfully'})
        except DeliveryPerson.DoesNotExist:
            return Response({'error': 'Courier not found or not available'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def take_order(self, request, pk=None):
        order = self.get_object()
        user = request.user

        # Проверяем, является ли пользователь курьером
        if not hasattr(user, 'deliveryperson'):
            return Response({'error': 'Только курьеры могут брать заказы.'}, status=status.HTTP_403_FORBIDDEN)

        courier = user.deliveryperson

        # Проверяем статус курьера
        if courier.status != 'available' or not courier.is_available:
            return Response({'error': 'Курьер не доступен для принятия заказа.'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем статус заказа
        if order.status not in ['pending', 'confirmed', 'preparing'] or order.delivery_person is not None:
            return Response({'error': 'Заказ не доступен для принятия или уже назначен.'}, status=status.HTTP_400_BAD_REQUEST)

        order.delivery_person = courier
        order.status = 'assigned'
        order.save()

        courier.status = 'busy'
        courier.is_available = False
        courier.save()

        broadcast_map_update()
        return Response({'status': 'Заказ успешно принят курьером.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        order = self.get_object()
        user = request.user

        # Проверяем, что заказ еще не доставлен или отменен
        if order.status in ['delivered', 'cancelled']:
            return Response({'error': 'Невозможно отменить заказ, который уже доставлен или отменен.'}, status=status.HTTP_400_BAD_REQUEST)

        # Разрешить отмену, если это курьер, которому назначен заказ, или админ
        if not user.is_staff and (not hasattr(user, 'deliveryperson') or order.delivery_person != user.deliveryperson):
            return Response({'error': 'У вас нет прав для отмены этого заказа.'}, status=status.HTTP_403_FORBIDDEN)

        # Если заказ был назначен курьеру, освобождаем курьера
        if order.delivery_person:
            courier = order.delivery_person
            courier.status = 'available'
            courier.is_available = True
            courier.save()

        order.status = 'cancelled'
        order.actual_delivery_time = timezone.now()
        order.save()
        broadcast_map_update()
        return Response({'status': 'Заказ успешно отменен.'}, status=status.HTTP_200_OK)

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

    @action(detail=True, methods=['get'])
    def get_route(self, request, pk=None):
        order = self.get_object()

        # Проверяем права доступа
        if request.user != order.delivery_person.user and not request.user.is_staff:
            return Response({'error': 'У вас нет прав для просмотра этого маршрута.'}, status=status.HTTP_403_FORBIDDEN)

        if not order.restaurant or not order.delivery_latitude or not order.delivery_longitude:
            return Response({'error': 'Недостаточно данных для построения маршрута (отсутствует ресторан или адрес доставки).'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем координаты ресторана и клиента
        restaurant_coords = (order.restaurant.latitude, order.restaurant.longitude)
        delivery_coords = (float(order.delivery_latitude), float(order.delivery_longitude))
        
        # Получаем тип транспортного средства курьера для более точного маршрута
        vehicle_type = order.delivery_person.vehicle_type if order.delivery_person else "car"

        try:
            dgis = DGISService()
            route_data = dgis.calculate_route(points=[restaurant_coords, delivery_coords], vehicle_type=vehicle_type)
            return Response(route_data)
        except Exception as e:
            return Response({'error': f'Ошибка при получении маршрута: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    def get_queryset(self):
        # Получаем текущий заказ со статусом 'cart' для пользователя
        # или пустой QuerySet, если такого заказа нет
        cart_order = Order.objects.filter(customer=self.request.user, status='cart').first()
        if cart_order:
            return OrderItem.objects.filter(order=cart_order)
        return OrderItem.objects.none()

    def perform_create(self, serializer):
        # Получаем или создаем заказ со статусом 'cart' для текущего пользователя
        cart_order, created = Order.objects.get_or_create(customer=self.request.user, status='cart')
        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        # Проверяем, существует ли уже этот товар в корзине
        existing_item = OrderItem.objects.filter(order=cart_order, product=product).first()

        if existing_item:
            # Если товар уже в корзине, обновляем количество
            existing_item.quantity += quantity
            existing_item.price = product.price # Обновляем цену, если она изменилась
            existing_item.save()
            serializer.instance = existing_item # Возвращаем обновленный объект
        else:
            # Если товара нет, создаем новый OrderItem
            serializer.save(order=cart_order, price=product.price)
        self.update_cart_total(cart_order)

    def perform_update(self, serializer):
        # Разрешаем обновление только для элементов в корзине текущего пользователя
        instance = self.get_object()
        if instance.order.status != 'cart' or instance.order.customer != self.request.user:
            raise serializers.ValidationError("Вы не можете обновить этот элемент заказа.")
        serializer.save()
        self.update_cart_total(instance.order)

    def perform_destroy(self, instance):
        # Разрешаем удаление только для элементов в корзине текущего пользователя
        if instance.order.status != 'cart' or instance.order.customer != self.request.user:
            raise serializers.ValidationError("Вы не можете удалить этот элемент заказа.")
        order = instance.order
        instance.delete()
        self.update_cart_total(order)

    def update_cart_total(self, order):
        # Пересчитываем общую сумму корзины
        total_amount = sum(item.product.price * item.quantity for item in order.orderitem_set.all())
        order.total_amount = total_amount
        order.save()

class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated] # Только авторизованные пользователи

    def get_queryset(self):
        user = self.request.user
        if user.is_staff: # Админ видит все выплаты
            return Payout.objects.all()
        elif hasattr(user, 'deliveryperson'): # Курьер видит только свои выплаты
            return Payout.objects.filter(delivery_person=user.deliveryperson)
        return Payout.objects.none() # Другие пользователи не видят выплаты

    def perform_create(self, serializer):
        # Автоматически связываем выплату с текущим курьером, если он не админ
        if not self.request.user.is_staff:
            try:
                delivery_person = self.request.user.deliveryperson
                serializer.save(delivery_person=delivery_person)
            except DeliveryPerson.DoesNotExist:
                raise serializers.ValidationError("Только курьеры или администраторы могут создавать выплаты.")
        else:
            serializer.save() # Админ может указать курьера вручную

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        # Клиент видит только свои платежи
        return Payment.objects.filter(order__customer=user)

    @action(detail=True, methods=['post'])
    def initiate(self, request, pk=None):
        # Здесь будет логика инициации платежа через сторонний API
        # Например, с PayBox, MBANK, Элькарт
        # Это заглушка, реальная интеграция будет здесь
        order = self.get_object().order # Получаем связанный заказ
        # Предположим, что мы получили URL для редиректа от платежного провайдера
        payment_url = f"https://example.com/payment?order_id={order.id}&amount={order.total_with_delivery}"
        return Response({'payment_url': payment_url, 'status': 'Payment initiated, redirect to URL'})

    @action(detail=True, methods=['post'])
    def callback(self, request, pk=None):
        # Здесь будет логика обработки колбэка от платежного провайдера
        # Обновление статуса платежа и заказа
        payment = self.get_object()
        status_from_provider = request.data.get('status') # Пример: 'success', 'fail'
        transaction_id_from_provider = request.data.get('transaction_id')

        if status_from_provider == 'success':
            payment.status = 'completed'
            payment.order.status = 'pending' # Заказ переходит в ожидание подтверждения
            payment.transaction_id = transaction_id_from_provider
            payment.order.save()
        else:
            payment.status = 'failed'
        payment.save()

        return Response({'status': f'Payment {payment.status}'})

class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Пользователь может видеть только свои токены устройств
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # При создании токена, автоматически привязываем его к текущему пользователю
        serializer.save(user=self.request.user)

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
            'payouts': drf_reverse('payout-list', request=request, format=format),       # Добавлено
            'payments': drf_reverse('payment-list', request=request, format=format),     # Добавлено
            'device-tokens': drf_reverse('device-token-list', request=request, format=format), # Добавлено
            'map': drf_reverse('map-data', request=request, format=format), # Изменено с map-list на map-data
            'register': drf_reverse('register', request=request, format=format),
            'token': drf_reverse('token_obtain_pair', request=request, format=format),
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

        # Генерация JWT-токенов
        refresh = TokenObtainPairSerializer.get_token(user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

# API для входа пользователя (получение токена)
# class LoginView(generics.CreateAPIView): # УДАЛЕНО: Используем TokenObtainPairView напрямую
#     serializer_class = AuthTokenSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data,
#                                            context={'request': request})
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']
#         token, created = Token.objects.get_or_create(user=user)
#         return Response({
#             'token': token.key,
#             'user_id': user.pk,
#             'email': user.email,
#             'username': user.username
#         })

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
