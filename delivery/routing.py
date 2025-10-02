from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/map/$', consumers.MapConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        'websocket': AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)

from django.urls import path

from .consumers import MapConsumer

websocket_urlpatterns = [
    path("ws/map/", MapConsumer.as_asgi()),
]
