from django.urls import path
from .consumers import MapConsumer

# Single source of websocket routes used by ASGI app in karakoldelivery.asgi
websocket_urlpatterns = [
    path("ws/map/", MapConsumer.as_asgi()),
]
