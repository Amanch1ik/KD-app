from typing import Any, Dict, List, Tuple

import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Order, DeliveryPerson
from .utils import send_push_notification

import logging
from decimal import Decimal
from django.db import transaction
from django.core.mail import send_mail
# Временно отключаем сложные зависимости
# from firebase_admin import messaging

logger = logging.getLogger(__name__)


def calculate_order_totals(order):
    """Calculate and set order totals and fees in a consistent, atomic way.

    This centralizes business logic for computing order totals, courier and service
    fees, and applying promo discounts. It avoids duplicating logic across views
    and serializers.
    """
    from .models import PromoCode

    with transaction.atomic():
        items = order.items.select_related('product').all()
        subtotal = sum((item.product.price * item.quantity for item in items), Decimal('0.00'))
        # Example fee calculations (could be replaced with config-driven logic)
        courier_fee = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
        service_fee = (subtotal * Decimal('0.02')).quantize(Decimal('0.01'))

        delivery_fee = Decimal('0.00')
        discount_amount = Decimal('0.00')

        # Apply promo code if present
        if getattr(order, 'promo_code', None):
            try:
                promo = PromoCode.objects.get(code=order.promo_code)
                d, delivery_fee, applied = promo.apply_discount(subtotal, delivery_fee)
                if applied:
                    discount_amount = Decimal(d)
            except PromoCode.DoesNotExist:
                logger.debug('Promo code not found: %s', order.promo_code)

        total = (subtotal + courier_fee + service_fee + delivery_fee) - discount_amount

        order.courier_fee = courier_fee
        order.service_fee = service_fee
        order.total_amount = total.quantize(Decimal('0.01'))
        order.save()

        return order

# Временно отключаем сложные сервисы
class DGISService:
    """Сервис для работы с API 2ГИС"""

    BASE_URL = "https://api.2gis.com/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.DGIS_API_KEY

    def calculate_route(
        self, points: List[Tuple[float, float]], vehicle_type: str = "car"
    ) -> Dict[str, Any]:
        """
        Рассчитывает маршрут между точками

        Args:
            points: Список точек в формате [(lat1, lon1), (lat2, lon2), ...]
            vehicle_type: Тип транспортного средства (car, bicycle, foot)

        Returns:
            Dict с информацией о маршруте
        """
        if len(points) < 2:
            raise ValueError("Необходимо минимум 2 точки для построения маршрута")

        url = f"{self.BASE_URL}/routing"

        # Формируем строку с точками маршрута
        points_str = "|".join([f"{lon},{lat}" for lat, lon in points])

        params = {
            "key": self.api_key,
            "points": points_str,
            "type": vehicle_type,
            "output": "json",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        vehicle_type: str = "car",
    ) -> Dict[str, Any]:
        """
        Получает матрицу расстояний между точками

        Args:
            origins: Список начальных точек [(lat1, lon1), ...]
            destinations: Список конечных точек [(lat1, lon1), ...]
            vehicle_type: Тип транспортного средства

        Returns:
            Dict с матрицей расстояний
        """
        url = f"{self.BASE_URL}/matrix"

        # Формируем строки с точками
        origins_str = "|".join([f"{lon},{lat}" for lat, lon in origins])
        destinations_str = "|".join([f"{lon},{lat}" for lat, lon in destinations])

        params = {
            "key": self.api_key,
            "origins": origins_str,
            "destinations": destinations_str,
            "type": vehicle_type,
            "output": "json",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def calculate_delivery_cost(
        self,
        distance_meters: float,
        base_rate: float = 80.0,
        rate_per_km: float = 20.0,
        min_cost: float = 80.0,
    ) -> float:
        """
        Рассчитывает стоимость доставки на основе расстояния

        Args:
            distance_meters: Расстояние в метрах
            base_rate: Базовая ставка
            rate_per_km: Ставка за километр
            min_cost: Минимальная стоимость

        Returns:
            float: Стоимость доставки
        """
        distance_km = distance_meters / 1000
        cost = base_rate + (distance_km * rate_per_km)
        return max(cost, min_cost)


class NotificationService:
    """Сервис для отправки уведомлений"""

    @staticmethod
    def send_email_notification(recipient, subject, message):
        """
        Отправка email-уведомления
        :param recipient: Email получателя
        :param subject: Тема письма
        :param message: Текст сообщения
        """
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [recipient],
                fail_silently=False,
            )
            logger.info(f"Email sent to {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    @staticmethod
    def send_push_notification(device_token, title, body):
        """
        Отправка push-уведомления через Firebase
        :param device_token: Токен устройства
        :param title: Заголовок уведомления
        :param body: Текст уведомления
        """
        try:
            # Временно отключаем Firebase
            # message = messaging.Message(
            #     notification=messaging.Notification(
            #         title=title,
            #         body=body
            #     ),
            #     token=device_token
            # )
            # response = messaging.send(message)
            # logger.info(f"Push notification sent: {response}")
            logging.info(f"Push notification: {title} - {body} для {device_token}")
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")

    @staticmethod
    def notify_order_status_change(order, new_status):
        """
        Уведомление о смене статуса заказа
        :param order: Объект заказа
        :param new_status: Новый статус заказа
        """
        # Email уведомление
        NotificationService.send_email_notification(
            order.customer.email,
            f"Статус заказа #{order.id} изменен",
            f"Статус вашего заказа изменен на: {new_status}"
        )

        # Push-уведомление (если есть токен устройства)
        try:
            # Временно отключаем Firebase
            # device_token = order.customer.devicetoken_set.first().registration_id
            # NotificationService.send_push_notification(
            #     device_token,
            #     "Статус заказа обновлен",
            #     f"Заказ #{order.id}: {new_status}"
            # )
            logging.warning(f"Push notification disabled for user {order.customer.username}")
        except Exception as e:
            logger.warning(f"No device token for user {order.customer.username}")

def assign_available_courier(order):
    """
    Временная заглушка для назначения курьера
    """
    from .models import DeliveryPerson
    
    # Получаем список активных курьеров
    available_couriers = DeliveryPerson.objects.filter(is_active=True)
    
    if available_couriers.exists():
        # Случайный выбор курьера
        courier = random.choice(available_couriers)
        order.courier = courier
        order.save()
        return courier
    
    return None

def send_push_notification(user, title, body):
    """
    Временная заглушка для отправки push-уведомлений
    """
    # Временно отключаем отправку уведомлений
    logging.info(f"Push notification: {title} - {body} для {user}")
    return True

def calculate_delivery_fee(order_amount):
    """
    Расчет стоимости доставки
    :param order_amount: Сумма заказа
    :return: Стоимость доставки
    """
    from decimal import Decimal

    if order_amount >= Decimal('500'):
        return Decimal('0')  # Бесплатная доставка
    elif order_amount >= Decimal('300'):
        return Decimal('50')  # Стандартная доставка
    else:
        return Decimal('100')  # Доставка для маленьких заказов

def validate_order_creation(order_data):
    """
    Валидация данных при создании заказа
    :param order_data: Словарь с данными заказа
    :return: Словарь с результатом валидации
    """
    errors = {}

    # Проверка суммы заказа
    if order_data.get('total_amount', 0) <= 0:
        errors['total_amount'] = 'Сумма заказа должна быть положительной'

    # Проверка номера телефона
    phone_number = order_data.get('phone_number', '')
    if not phone_number or len(phone_number) < 10:
        errors['phone_number'] = 'Некорректный номер телефона'

    # Проверка адреса доставки
    delivery_address = order_data.get('delivery_address', '')
    if not delivery_address or len(delivery_address.strip()) == 0:
        errors['delivery_address'] = 'Адрес доставки не может быть пустым'

    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }
