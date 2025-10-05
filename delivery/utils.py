from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import os
import json
import requests

from .models import DeliveryPerson, Order, Restaurant
from .serializers import (DeliveryPersonSerializer, OrderSerializer,
                          RestaurantSerializer)


def broadcast_map_update():
    """Отправляет свежие данные карты во все WebSocket-клиенты"""
    delivery_persons = DeliveryPerson.objects.filter(is_available=True)
    active_orders = Order.objects.filter(
        status__in=["assigned", "picked_up", "delivering"]
    )
    restaurants = Restaurant.objects.filter(is_active=True)

    data = {
        "delivery_persons": DeliveryPersonSerializer(delivery_persons, many=True).data,
        "active_orders": OrderSerializer(active_orders, many=True).data,
        "restaurants": RestaurantSerializer(restaurants, many=True).data,
    }

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "map_updates", {"type": "map_update", "data": data}
    )


def send_push_notification(user_or_tokens, title, message, data=None):
    """Отправляет push-уведомление пользователю или на список токенов устройств.
    user_or_tokens: Может быть объектом User, DeliveryPerson, или списком строк (registration_id).
    """
    registration_ids = []

    if isinstance(user_or_tokens, list):
        registration_ids = user_or_tokens
    elif hasattr(user_or_tokens, "device_tokens"):
        # Если это объект User или DeliveryPerson, получаем связанные токены
        registration_ids = [
            dt.registration_id for dt in user_or_tokens.device_tokens.all()
        ]
    elif hasattr(user_or_tokens, "user") and hasattr(
        user_or_tokens.user, "device_tokens"
    ):
        # Если это DeliveryPerson, получаем токены через связанного User
        registration_ids = [
            dt.registration_id for dt in user_or_tokens.user.device_tokens.all()
        ]

    if not registration_ids:
        print(
            f"No device tokens found for {user_or_tokens}. Not sending push notification."
        )
        return

    server_key = os.getenv("FCM_SERVER_KEY")
    if not server_key:
        print("FCM_SERVER_KEY is not set; skipping push send.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"key={server_key}",
    }
    payload = {
        "registration_ids": registration_ids,
        "notification": {"title": title, "body": message},
        "data": data or {},
        "android": {"priority": "high"},
        "apns": {"headers": {"apns-priority": "10"}},
    }
    try:
        response = requests.post(
            "https://fcm.googleapis.com/fcm/send", headers=headers, data=json.dumps(payload)
        )
        print(f"FCM response: {response.status_code} {response.text}")
    except Exception as e:
        print(f"FCM send error: {e}")
