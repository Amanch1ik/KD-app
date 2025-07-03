from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import DeliveryPerson, Order, Restaurant
from .serializers import DeliveryPersonSerializer, OrderSerializer, RestaurantSerializer


def broadcast_map_update():
    """Отправляет свежие данные карты во все WebSocket-клиенты"""
    delivery_persons = DeliveryPerson.objects.filter(is_available=True)
    active_orders = Order.objects.filter(status__in=['assigned', 'picked_up', 'delivering'])
    restaurants = Restaurant.objects.filter(is_active=True)

    data = {
        'delivery_persons': DeliveryPersonSerializer(delivery_persons, many=True).data,
        'active_orders': OrderSerializer(active_orders, many=True).data,
        'restaurants': RestaurantSerializer(restaurants, many=True).data,
    }

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'map_updates',
        {
            'type': 'map_update',
            'data': data
        }
    ) 