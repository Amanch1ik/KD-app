from django.urls import path
from .consumers import MapConsumer

websocket_urlpatterns = [
    path('ws/map/', MapConsumer.as_asgi()),
] 