import logging
import secrets
from datetime import timedelta

import requests  # Добавляем импорт requests
from django.contrib.auth import get_user_model
User = get_user_model()
from django.db import models, transaction
from django.utils import timezone
from django.db.models import Sum, F
from rest_framework import generics, serializers, status, viewsets, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.reverse import reverse as drf_reverse
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import activate
from django.shortcuts import redirect
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.parsers import (
    FormParser, 
    MultiPartParser, 
    JSONParser
)
from django.http import JsonResponse
from django.utils import translation

from .models import (Category, DeliveryPerson, DeliveryTracking, DeliveryZone,
                     DeviceToken, Order, OrderItem, Payment, Payout, Product,
                     Rating, Restaurant, PasswordResetToken)
from .serializers import (CategorySerializer, DeliveryPersonDocumentSerializer,
                          DeliveryPersonSerializer, DeliveryTrackingSerializer,
                          DeliveryZoneSerializer, DeviceTokenSerializer,
                          LocationUpdateSerializer, OrderItemSerializer,
                          OrderSerializer, PaymentSerializer, PayoutSerializer,
                          ProductSerializer, RatingSerializer,
                          RestaurantSerializer, UserRegistrationSerializer,
                          UserSerializer, PasswordResetRequestSerializer,
                          PasswordResetConfirmSerializer)
from .services import DGISService, assign_available_courier
from .utils import send_push_notification, broadcast_map_update
from rest_framework import viewsets, permissions
from .models import UserProfile
from .serializers import UserProfileSerializer

logger = logging.getLogger(__name__)



class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'name']
    permission_classes = [IsAuthenticatedOrReadOnly]
    # Добавляем поиск по имени и описанию

    def get_queryset(self):
        queryset = super().get_queryset()
        restaurant_id = self.request.query_params.get("restaurant")
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        return queryset

    @action(detail=False, methods=["get"])
    def by_category(self, request):
        category_id = request.query_params.get("category_id")
        if category_id:
            products = Product.objects.filter(
                category_id=category_id, available=True
            )
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "category_id parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def by_restaurant(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            products = Product.objects.filter(
                restaurant_id=restaurant_id, available=True
            )
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response(
            {"error": "restaurant parameter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DeliveryZoneViewSet(viewsets.ModelViewSet):
    queryset = DeliveryZone.objects.filter(is_active=True)
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# New Menu API endpoint scaffold, reusing existing Product view logic
class MenuViewSet(ProductViewSet):
    pass


class CartViewSet(viewsets.ViewSet):
    """Scaffold: basic cart endpoints for authenticated users"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        cart_order = Order.objects.filter(customer=request.user, status="cart").first()
        if not cart_order:
            return Response({"order_id": None, "items": [], "total": 0})

        items = cart_order.items.all()
        serializer = OrderItemSerializer(items, many=True)
        total = cart_order.items.aggregate(total=Sum(F("quantity") * F("price")))["total"] or 0
        return Response({"order_id": cart_order.id, "items": serializer.data, "total": total})

    def create(self, request):
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity", 1))
        if not product_id:
            return Response({"error": "product is required"}, status=status.HTTP_400_BAD_REQUEST)

        cart_order, _ = Order.objects.get_or_create(customer=request.user, status="cart")
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        existing_item = OrderItem.objects.filter(order=cart_order, product=product).first()
        if existing_item:
            existing_item.quantity += quantity
            existing_item.price = product.price
            existing_item.save()
            serializer_instance = existing_item
        else:
            serializer_instance = OrderItem.objects.create(
                order=cart_order, product=product, quantity=quantity, price=product.price
            )
        self._update_cart_total(cart_order)
        items = cart_order.items.all()
        serializer = OrderItemSerializer(items, many=True)
        total = cart_order.items.aggregate(total=Sum(F("quantity") * F("price"))) ["total"] or 0
        return Response({"order_id": cart_order.id, "items": serializer.data, "total": total})

    def _update_cart_total(self, order):
        total = order.items.aggregate(total=Sum(F("quantity") * F("price")))["total"] or 0
        order.total_amount = total
        order.save()

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        """Checkout cart: convert cart to pending/confirmed order"""
        cart_order = Order.objects.filter(customer=request.user, status="cart").first()
        if not cart_order:
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Allow optional override of address/phone in checkout payload
        delivery_address = request.data.get("delivery_address")
        phone_number = request.data.get("phone_number")
        if delivery_address:
            cart_order.delivery_address = delivery_address
        if phone_number:
            cart_order.phone_number = phone_number
        cart_order.status = "pending"
        cart_order.save()
        self.update_cart_total(cart_order)
        serializer = OrderSerializer(cart_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeliveryPersonViewSet(viewsets.ModelViewSet):
    queryset = DeliveryPerson.objects.all()
    serializer_class = DeliveryPersonSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def update_location(self, request, pk=None):
        delivery_person = self.get_object()
        serializer = LocationUpdateSerializer(data=request.data)

        if serializer.is_valid():
            delivery_person.current_latitude = (
                serializer.validated_data["latitude"]
            )
            delivery_person.current_longitude = (
                serializer.validated_data["longitude"]
            )
            if "status" in serializer.validated_data:
                delivery_person.status = serializer.validated_data["status"]
            delivery_person.save()

            # Создаем запись отслеживания для активных заказов
            active_orders = Order.objects.filter(
                delivery_person=delivery_person,
                status__in=["assigned", "picked_up", "delivering"],
            )

            for order in active_orders:
                DeliveryTracking.objects.create(
                    order=order,
                    delivery_person=delivery_person,
                    latitude=delivery_person.current_latitude,
                    longitude=delivery_person.current_longitude,
                    status=delivery_person.status,
                )

            broadcast_map_update()
            return Response({"status": "Location updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def available(self, request):
        available_persons = DeliveryPerson.objects.filter(
            is_available=True, status="available"
        )
        serializer = self.get_serializer(available_persons, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch", "put"])
    def upload_documents(self, request, pk=None):
        delivery_person = self.get_object()
        # Проверяем, что запрос делает сам курьер или администратор
        if request.user != delivery_person.user and not request.user.is_staff:
            return Response(
                {"error": "У вас нет прав для выполнения этого действия."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DeliveryPersonDocumentSerializer(
            delivery_person, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def get_balance(self, request, pk=None):
        delivery_person = self.get_object()
        if request.user != delivery_person.user and not request.user.is_staff:
            return Response(
                {"error": "У вас нет прав для просмотра этого баланса."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Сумма всех заработанных комиссий курьера
        total_earned = (
            Order.objects.filter(
                delivery_person=delivery_person, status="delivered"
            ).aggregate(total=models.Sum("courier_fee"))["total"]
            or 0
        )

        # Сумма всех выплат курьеру
        total_paid = (
            Payout.objects.filter(delivery_person=delivery_person).aggregate(
                total=models.Sum("amount")
            )["total"]
            or 0
        )

        current_balance = total_earned - total_paid

        return Response(
            {
                "delivery_person_id": delivery_person.id,
                "total_earned": total_earned,
                "total_paid": total_paid,
                "current_balance": current_balance,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def get_stats(self, request, pk=None):
        delivery_person = self.get_object()
        if request.user != delivery_person.user and not request.user.is_staff:
            return Response(
                {"error": "У вас нет прав для просмотра статистики."},
                status=status.HTTP_403_FORBIDDEN,
            )

        completed_orders_count = Order.objects.filter(
            delivery_person=delivery_person, status="delivered"
        ).count()
        total_delivery_fee_earned = (
            Order.objects.filter(
                delivery_person=delivery_person, status="delivered"
            ).aggregate(total=models.Sum("courier_fee"))["total"]
            or 0
        )

        return Response(
            {
                "delivery_person_id": delivery_person.id,
                "completed_orders_count": completed_orders_count,
                "total_delivery_fee_earned": total_delivery_fee_earned,
            },
            status=status.HTTP_200_OK,
        )


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(is_active=True)
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ["name", "address"]  # Добавляем поиск по имени и адресу
    # filterset_fields = ['is_active', 'avg_rating'] # Убираем django-filter


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    # filterset_fields = ['status', 'delivery_person',  # Убираем django-filter
    #                   'customer', 'created_at']
    search_fields = [
        "order_id",
        "delivery_address",
        "customer_name",
        "phone_number",
    ]  # Добавляем поля для поиска

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all().select_related(
                'customer', 'delivery_person', 'restaurant', 'delivery_zone'
            ).prefetch_related(
                'items__product'
            )

        # Проверяем, является ли пользователь курьером
        if hasattr(user, "deliveryperson"):
            courier = user.deliveryperson
            # Курьер видит свои заказы и доступные (неназначенные)
            return Order.objects.filter(
                models.Q(delivery_person=courier)
                | models.Q(
                    status__in=["pending", "confirmed", "preparing"],
                    delivery_person__isnull=True,
                )
            ).distinct().select_related(
                'customer', 'delivery_person', 'restaurant', 'delivery_zone'
            ).prefetch_related(
                'items__product'
            )

        # Клиент видит только свои заказы
        return Order.objects.filter(customer=user).select_related(
            'customer', 'delivery_person', 'restaurant', 'delivery_zone'
        ).prefetch_related(
            'items__product'
        )

    def perform_create(self, serializer):
        order = serializer.save(customer=self.request.user)
        # If there is a cart with items for this user, move them to the new order
        cart_order = Order.objects.filter(customer=self.request.user, status="cart").first()
        if cart_order:
            for cart_item in cart_order.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.price,
                )
            total = order.items.aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0
            order.total_amount = total
            order.save()
            cart_order.delete()
            cart_order.delete()

        # Пытаемся назначить курьера через сервис
        courier_assigned = assign_available_courier(order)

        if not courier_assigned:
            logger.info(f"No available courier found for order {order.order_id}.")


        if not order.restaurant and order.items.exists():
            first_item_product_restaurant = order.items.first().product.restaurant
            if first_item_product_restaurant:
                order.restaurant = first_item_product_restaurant
                order.save()

    @action(detail=True, methods=["post"])
    def assign_courier(self, request, pk=None):
        # Только администраторы или партнеры ресторана могут назначать курьера
        user = request.user
        if not user.is_staff and (
            not hasattr(user, "profile") or user.profile.role != "restaurant_partner"
        ):
            return Response(
                {"error": "У вас нет прав для назначения курьера."},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_object()
        courier_id = request.data.get("courier_id")

        try:
            courier = DeliveryPerson.objects.get(id=courier_id, is_available=True)
            # Освобождаем предыдущего курьера (если был)
            if order.delivery_person and order.delivery_person != courier:
                prev = order.delivery_person
                prev.status = "available"
                prev.is_available = True
                prev.save()

            # Назначаем нового
            order.delivery_person = courier
            order.status = "assigned"
            order.save()

            # Обновляем статус курьера
            courier.status = "busy"
            courier.is_available = False
            courier.save()

            broadcast_map_update()
            # Отправляем push-уведомление курьеру
            send_push_notification(
                user_or_tokens=courier.user,
                title="Заказ назначен!",
                message=(
                    f"Вам назначен заказ #{order.order_id} на "
                    f"сумму {order.total_with_delivery} сом."
                ),
            )
            return Response({"status": "Courier assigned successfully"})
        except DeliveryPerson.DoesNotExist:
            return Response(
                {"error": "Courier not found or not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def take_order(self, request, pk=None):
        try:
            order = self.get_object()
            user = request.user

            # Проверяем, является ли пользователь курьером
            if not hasattr(user, "deliveryperson"):
                return Response(
                    {
                        "error": "Только курьеры могут брать заказы.",
                        "code": "not_courier",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            courier = user.deliveryperson

            # Проверяем статус курьера
            if courier.status != "available" or not courier.is_available:
                return Response(
                    {
                        "error": "Курьер не доступен для принятия заказа.",
                        "code": "courier_unavailable",
                        "current_status": courier.status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Проверяем статус заказа
            if (
                order.status not in ["pending", "confirmed", "preparing"]
                or order.delivery_person is not None
            ):
                return Response(
                    {
                        "error": "Заказ не доступен для принятия или уже назначен.",
                        "code": "order_unavailable",
                        "current_status": order.status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Блокируем заказ для предотвращения одновременного принятия
            with transaction.atomic():
                # Проверяем, не был ли заказ уже принят другим курьером
                order_refresh = Order.objects.select_for_update().get(pk=order.pk)
                if order_refresh.delivery_person is not None:
                    return Response(
                        {
                            "error": "Заказ уже был принят другим курьером.",
                            "code": "order_already_taken",
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                order.delivery_person = courier
                order.status = "assigned"
                order.save()

                courier.status = "busy"
                courier.is_available = False
                courier.save()

            broadcast_map_update()
            return Response(
                {"status": "Заказ успешно принят курьером.", "order_id": order.id}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error taking order: {e}")
            return Response(
                {
                    "error": "Произошла непредвиденная ошибка при принятии заказа.",
                    "code": "unexpected_error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def cancel_order(self, request, pk=None):
        try:
            order = self.get_object()
            user = request.user

            # Проверяем, что заказ еще не доставлен или отменен
            if order.status in ["delivered", "cancelled"]:
                return Response(
                    {
                        "error": "Невозможно отменить заказ, который уже доставлен или отменен.",
                        "code": "order_completed",
                        "current_status": order.status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Разрешить отмену, если это клиент, который создал заказ, или администратор
            if not user.is_staff and order.customer != user:
                return Response(
                    {
                        "error": "У вас нет прав для отмены этого заказа.",
                        "code": "not_authorized",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Блокируем заказ для безопасного обновления
            with transaction.atomic():
                # Если заказ был назначен курьеру, освобождаем курьера
                if order.delivery_person:
                    courier = order.delivery_person
                    courier.status = "available"
                    courier.is_available = True
                    courier.save()

                order.status = "cancelled"
                order.actual_delivery_time = timezone.now()
                order.save()

            broadcast_map_update()
            return Response(
                {
                    "status": "Заказ успешно отменен.", 
                    "order_id": order.id
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return Response(
                {
                    "error": "Произошла непредвиденная ошибка при отмене заказа.",
                    "code": "unexpected_error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        try:
            order = self.get_object()
            new_status = request.data.get("status")
            user = request.user

            # Проверка базовых разрешений: только администратор или назначенный курьер или партнер ресторана
            is_admin = user.is_staff
            is_delivery_person = (
                hasattr(user, "deliveryperson")
                and order.delivery_person == user.deliveryperson
            )
            is_restaurant_partner = (
                hasattr(user, "profile")
                and user.profile.role == "restaurant_partner"
                and order.restaurant
                and order.restaurant.partner_user == user.profile
            )

            if not (is_admin or is_delivery_person or is_restaurant_partner):
                return Response(
                    {
                        "error": "У вас нет прав для изменения статуса этого заказа.",
                        "code": "not_authorized",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Проверяем корректность нового статуса
            if new_status not in dict(Order.STATUS_CHOICES):
                return Response(
                    {
                        "error": "Недопустимый статус",
                        "code": "invalid_status",
                        "allowed_statuses": dict(Order.STATUS_CHOICES),
                    }, 
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Более детальные проверки на основе ролей и нового статуса
            if is_admin:  # Администратор может устанавливать любой статус
                pass
            elif is_delivery_person:  # Курьер может устанавливать только статусы, связанные с доставкой
                if new_status not in ["picked_up", "delivering", "delivered"]:
                    return Response(
                        {
                            "error": 'Курьер может изменять статус только на "забрал", "доставляется" или "доставлен".',
                            "code": "invalid_courier_status",
                            "allowed_statuses": ["picked_up", "delivering", "delivered"],
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            elif is_restaurant_partner:  # Партнер ресторана может устанавливать только статус "готовится"
                if new_status != "preparing":
                    return Response(
                        {
                            "error": 'Партнер ресторана может изменять статус только на "готовится".',
                            "code": "invalid_partner_status",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

            # Блокируем заказ для безопасного обновления
            with transaction.atomic():
                order.status = new_status
                if new_status in ["delivered", "cancelled"]:
                    order.actual_delivery_time = timezone.now()
                    # Освобождаем курьера
                    if order.delivery_person:
                        dp = order.delivery_person
                        dp.status = "available"
                        dp.is_available = True
                        dp.save()
                order.save()

            broadcast_map_update()
            return Response(
                {
                    "status": "Статус заказа обновлен успешно", 
                    "order_id": order.id, 
                    "new_status": new_status
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return Response(
                {
                    "error": "Произошла непредвиденная ошибка при обновлении статуса заказа.",
                    "code": "unexpected_error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def rate(self, request, pk=None):
        """Клиент оценивает доставку (1-5)"""
        order = self.get_object()
        if order.customer != request.user:
            return Response(
                {"error": "Можно оценивать только свои заказы"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if order.status != "delivered":
            return Response(
                {"error": "Оценка доступна только для доставленных заказов"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if hasattr(order, "rating"):
            return Response(
                {"error": "Заказ уже оценён"}, status=status.HTTP_400_BAD_REQUEST
            )

        score = int(request.data.get("score", 0))
        comment = request.data.get("comment", "")
        if score < 1 or score > 5:
            return Response(
                {"error": "Оценка от 1 до 5"}, status=status.HTTP_400_BAD_REQUEST
            )

        rating = Rating.objects.create(
            order=order,
            courier=order.delivery_person,
            restaurant=order.restaurant,
            score=score,
            comment=comment,
        )
        broadcast_map_update()
        return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def tracking(self, request, pk=None):
        order = self.get_object()
        tracking_data = DeliveryTracking.objects.filter(order=order).order_by(
            "-timestamp"
        )
        serializer = DeliveryTrackingSerializer(tracking_data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def get_route(self, request, pk=None):
        order = self.get_object()

        # Проверяем права доступа
        if request.user != order.delivery_person.user and not request.user.is_staff:
            return Response(
                {"error": "У вас нет прав для просмотра этого маршрута."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            not order.restaurant
            or not order.delivery_latitude
            or not order.delivery_longitude
        ):
            return Response(
                {
                    "error": (
                        "Недостаточно данных для построения маршрута "
                        "(отсутствует ресторан или адрес доставки)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Получаем координаты ресторана и клиента
        restaurant_coords = (order.restaurant.latitude, order.restaurant.longitude)
        delivery_coords = (
            float(order.delivery_latitude),
            float(order.delivery_longitude),
        )

        # Получаем тип транспортного средства курьера для более точного маршрута
        vehicle_type = (
            order.delivery_person.vehicle_type if order.delivery_person else "car"
        )

        try:
            dgis = DGISService()
            route_data = dgis.calculate_route(
                points=[restaurant_coords, delivery_coords], vehicle_type=vehicle_type
            )
            return Response(route_data, status=status.HTTP_200_OK)
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Ошибка при запросе к 2ГИС API для маршрута "
                f"заказа {order.order_id}: {e}"
            )
            return Response(
                {"error": "Ошибка при запросе к сервису маршрутов."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )  # 503 Service Unavailable
        except Exception as e:
            logger.error(
                f"Неизвестная ошибка при получении маршрута "
                f"для заказа {order.order_id}: {e}"
            )
            return Response(
                {"error": f"Ошибка при получении маршрута: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
        cart_order = Order.objects.filter(
            customer=self.request.user, status="cart"
        ).first()
        if cart_order:
            return OrderItem.objects.filter(order=cart_order)
        return OrderItem.objects.none()

    def perform_create(self, serializer):
        # Получаем или создаем заказ со статусом 'cart' для текущего пользователя
        cart_order, created = Order.objects.get_or_create(
            customer=self.request.user, status="cart"
        )
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        # Проверяем, существует ли уже этот товар в корзине
        existing_item = OrderItem.objects.filter(
            order=cart_order, product=product
        ).first()

        if existing_item:
            # Если товар уже в корзине, обновляем количество
            existing_item.quantity += quantity
            existing_item.price = product.price  # Обновляем цену, если она изменилась
            existing_item.save()
            serializer.instance = existing_item  # Возвращаем обновленный объект
        else:
            # Если товара нет, создаем новый OrderItem
            serializer.save(order=cart_order, price=product.price)
        self.update_cart_total(cart_order)

    def perform_update(self, serializer):
        # Разрешаем обновление только для элементов в корзине текущего пользователя
        instance = self.get_object()
        if (
            instance.order.status != "cart"
            or instance.order.customer != self.request.user
        ):
            raise serializers.ValidationError(
                "Вы не можете обновить этот элемент заказа."
            )
        serializer.save()
        self.update_cart_total(instance.order)

    def perform_destroy(self, instance):
        # Разрешаем удаление только для элементов в корзине текущего пользователя
        if (
            instance.order.status != "cart"
            or instance.order.customer != self.request.user
        ):
            raise serializers.ValidationError(
                "Вы не можете удалить этот элемент заказа."
            )
        order = instance.order
        instance.delete()
        self.update_cart_total(order)

    def update_cart_total(self, order):
        # Пересчитываем общую сумму корзины
        total_amount = order.items.aggregate(
            total=models.Sum(models.F('quantity') * models.F('price'))
        )['total'] or 0
        order.total_amount = total_amount
        order.save()


class RatingViewSet(viewsets.ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated]  # Только авторизованные пользователи

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:  # Админ видит все выплаты
            return Payout.objects.all()
        elif hasattr(user, "deliveryperson"):  # Курьер видит только свои выплаты
            return Payout.objects.filter(delivery_person=user.deliveryperson)
        return Payout.objects.none()  # Другие пользователи не видят выплаты

    def perform_create(self, serializer):
        # Автоматически связываем выплату с текущим курьером, если он не админ
        if not self.request.user.is_staff:
            try:
                delivery_person = self.request.user.deliveryperson
                serializer.save(delivery_person=delivery_person)
            except DeliveryPerson.DoesNotExist:
                raise serializers.ValidationError(
                    "Только курьеры или администраторы могут создавать выплаты."
                )
        else:
            serializer.save()  # Админ может указать курьера вручную


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # При генерации схемы или для анонимного пользователя возвращаем пустой queryset
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return Payment.objects.none()
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        # Клиент видит только свои платежи
        return Payment.objects.filter(order__customer=user)

    @action(detail=True, methods=["post"])
    def initiate(self, request, pk=None):
        # Инициация платежа через Stripe (checkout session)
        stripe = None
        try:
            import stripe as _stripe  # type: ignore
            stripe = _stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY
        except Exception:
            stripe = None

        if stripe is None:
            return Response({"error": "Stripe library not installed"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        payment = self.get_object()
        order = payment.order

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'kgs',
                            'product_data': {'name': f'Order {order.id}'},
                            'unit_amount': int(order.total_amount * 100),
                        },
                        'quantity': 1,
                    }
                ],
                mode='payment',
                success_url=f"{settings.FRONTEND_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/payment-cancel",
            )
            return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Stripe session creation failed: {e}")
            return Response({"error": "Payment initiation failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def callback(self, request, pk=None):
        # Здесь будет логика обработки колбэка от платежного провайдера
        # Обновление статуса платежа и заказа
        payment = self.get_object()
        status_from_provider = request.data.get("status")  # Example: 'success', 'fail'
        transaction_id_from_provider = request.data.get("transaction_id")

        # For Stripe webhooks this logic should be moved to a dedicated webhook handler
        if status_from_provider == "success":
            payment.status = "completed"
            payment.order.status = "confirmed"
            payment.transaction_id = transaction_id_from_provider
            payment.order.save()
        else:
            payment.status = "failed"
        payment.save()
        return Response({"status": f"Payment {payment.status}"})


class DeviceTokenViewSet(viewsets.ModelViewSet):
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # При генерации схемы или для анонимного пользователя возвращаем пустой queryset
        if (
            getattr(self, "swagger_fake_view", False)
            or not self.request.user.is_authenticated
        ):
            return DeviceToken.objects.none()
        # Пользователь может видеть только свои токены устройств
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # При создании токена, автоматически привязываем его к текущему пользователю
        serializer.save(user=self.request.user)


# Специальное представление для карты
class MapViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=False, methods=["get"])
    def data(self, request):
        """Получить все данные для отображения на карте"""
        delivery_persons = DeliveryPerson.objects.filter(is_available=True)
        active_orders = Order.objects.filter(
            status__in=["assigned", "picked_up", "delivering"]
        )
        restaurants = Restaurant.objects.filter(is_active=True)

        data = {
            "delivery_persons": DeliveryPersonSerializer(
                delivery_persons, many=True
            ).data,
            "active_orders": OrderSerializer(active_orders, many=True).data,
            "restaurants": RestaurantSerializer(restaurants, many=True).data,
        }

        return Response(data)

    @action(detail=False, methods=["get"])
    def delivery_persons(self, request):
        """Получить только курьеров для карты"""
        delivery_persons = DeliveryPerson.objects.filter(is_available=True)
        serializer = DeliveryPersonSerializer(delivery_persons, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def active_orders(self, request):
        """Получить только активные заказы для карты"""
        active_orders = Order.objects.filter(
            status__in=["assigned", "picked_up", "delivering"]
        )
        serializer = OrderSerializer(active_orders, many=True)
        return Response(serializer.data)


# Custom API Root View
class ApiRoot(APIView):
    def get(self, request, format=None):
        return Response(
            {
                "categories": drf_reverse(
                    "category-list", request=request, format=format
                ),
                "products": drf_reverse("product-list", request=request, format=format),
                "orders": drf_reverse("order-list", request=request, format=format),
                "delivery-zones": drf_reverse(
                    "deliveryzone-list", request=request, format=format
                ),
                "delivery-persons": drf_reverse(
                    "deliveryperson-list", request=request, format=format
                ),
                "restaurants": drf_reverse(
                    "restaurant-list", request=request, format=format
                ),
                "delivery-tracking": drf_reverse(
                    "deliverytracking-list", request=request, format=format
                ),
                "order-items": drf_reverse(
                    "orderitem-list", request=request, format=format
                ),
                "ratings": drf_reverse("rating-list", request=request, format=format),
                "payouts": drf_reverse("payout-list", request=request, format=format),
                "payments": drf_reverse("payment-list", request=request, format=format),
                "device-tokens": drf_reverse(
                    "device-token-list", request=request, format=format
                ),
                "map": drf_reverse("map-data", request=request, format=format),
                "register": drf_reverse("register", request=request, format=format),
                "token": drf_reverse(
                    "token_obtain_pair", request=request, format=format
                ),
                "user-profile": drf_reverse(
                    "user-profile", request=request, format=format
                ),
            }
        )


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
        return Response(
            {
                "user": UserSerializer(
                    user, context=self.get_serializer_context()
                ).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (
        MultiPartParser,
        FormParser,
    )  # Добавляем парсеры для обработки файлов

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Дополнительная фильтрация профилей
        """
        queryset = super().get_queryset()
        
        # Фильтрация по параметрам запроса
        role = self.request.query_params.get('role', None)
        language = self.request.query_params.get('language', None)
        notification_settings = self.request.query_params.get('notification_settings', None)
        
        params = {}
        if role:
            params['role'] = role
        if language:
            params['language'] = language
        if notification_settings:
            params['notification_settings'] = notification_settings
        
        serializer = self.get_serializer()
        return serializer.filter_queryset(queryset, params)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Initiate password reset process
    Sends a secure token to user's email
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Prevent email enumeration
            logger.info(f'Password reset requested for non-existent email: {email}')
            return Response({
                'detail': 'If an account exists with this email, a reset link will be sent.'
            }, status=status.HTTP_200_OK)
        
        # Generate a secure token
        token = secrets.token_urlsafe(32)
        
        # Create or update password reset token
        reset_token, created = PasswordResetToken.objects.get_or_create(
            user=user,
            defaults={
                'token': token,
                'created_at': timezone.now(),
                'expires_at': timezone.now() + timedelta(hours=1)
            }
        )
        
        if not created:
            # Update existing token
            reset_token.token = token
            reset_token.created_at = timezone.now()
            reset_token.expires_at = timezone.now() + timedelta(hours=1)
            reset_token.save()
        
        # Send email with reset link
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        
        try:
            send_mail(
                'Password Reset Request',
                f'Click the following link to reset your password: {reset_link}\n'
                'This link will expire in 1 hour.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            logger.info(f'Password reset link sent to {email}')
        except Exception as e:
            logger.error(f'Failed to send password reset email: {e}')
            return Response({
                'detail': 'Error sending reset email. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'detail': 'If an account exists with this email, a reset link will be sent.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Confirm password reset using a secure token
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    
    if serializer.is_valid():
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            # Find valid token
            reset_token = PasswordResetToken.objects.get(
                token=token,
                expires_at__gt=timezone.now()
            )
        except PasswordResetToken.DoesNotExist:
            logger.warning(f'Invalid or expired password reset token used')
            return Response({
                'detail': 'Invalid or expired reset token.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = reset_token.user
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        # Invalidate the token
        reset_token.delete()
        
        logger.info(f'Password successfully reset for user {user.email}')
        
        return Response({
            'detail': 'Password reset successful.'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change password for authenticated users
    """
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response({
            'detail': 'Both old and new passwords are required.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    # Check old password
    if not user.check_password(old_password):
        logger.warning(f'Failed password change attempt for user {user.email}')
        return Response({
            'detail': 'Incorrect old password.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    logger.info(f'Password successfully changed for user {user.email}')
    
    return Response({
        'detail': 'Password changed successfully.'
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def set_language_view(request):
    """
    Обработчик для смены языка
    """
    language = request.GET.get('language', 'ru')
    
    if language in ['ru', 'ky', 'en']:
        translation.activate(language)
        response = JsonResponse({'status': 'success', 'language': language})
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
        return response
    
    return JsonResponse({'status': 'error', 'message': 'Invalid language'}, status=400)

