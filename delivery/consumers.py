from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import DeliveryPerson, Order, Restaurant
from .serializers import DeliveryPersonSerializer, OrderSerializer, RestaurantSerializer


class MapConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('map_updates', self.channel_name)
        await self.accept()
        await self.send_initial()

    async def disconnect(self, code):
        await self.channel_layer.group_discard('map_updates', self.channel_name)

    @database_sync_to_async
    def get_data(self):
        delivery_persons = DeliveryPerson.objects.filter(is_available=True)
        active_orders = Order.objects.filter(status__in=['assigned', 'picked_up', 'delivering'])
        restaurants = Restaurant.objects.filter(is_active=True)
        return {
            'delivery_persons': DeliveryPersonSerializer(delivery_persons, many=True).data,
            'active_orders': OrderSerializer(active_orders, many=True).data,
            'restaurants': RestaurantSerializer(restaurants, many=True).data,
        }

    async def send_initial(self):
        data = await self.get_data()
        await self.send_json({'type': 'initial', 'payload': data})

    async def map_update(self, event):
        await self.send_json({'type': 'update', 'payload': event['data']}) 