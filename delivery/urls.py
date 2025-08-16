from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, DeliveryZoneViewSet, DeliveryPersonViewSet,
    OrderViewSet, OrderItemViewSet, DeliveryTrackingViewSet, RestaurantViewSet,
    RatingViewSet, home, map_view, UserProfileView, RegisterView, MapViewSet # ApiRoot удалена из импорта
)
from .views import PayoutViewSet, PaymentViewSet, DeviceTokenViewSet # Добавляем PaymentViewSet и DeviceTokenViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'delivery-zones', DeliveryZoneViewSet)
router.register(r'delivery-persons', DeliveryPersonViewSet)
router.register(r'restaurants', RestaurantViewSet)
router.register(r'delivery-tracking', DeliveryTrackingViewSet)
router.register(r'order-items', OrderItemViewSet)
router.register(r'ratings', RatingViewSet)
router.register(r'map', MapViewSet, basename='map')
router.register(r'payouts', PayoutViewSet, basename='payout')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'device-tokens', DeviceTokenViewSet, basename='device-token') # Добавляем DeviceTokenViewSet

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('', home, name='home'),
    path('map/', map_view, name='map'),
]

# Custom API Root View # УДАЛЕНО: Этот класс теперь определяется в karakoldelivery/urls.py
# class ApiRoot(APIView):
#     def get(self, request, format=None):
#         return Response({
#             'categories': drf_reverse('category-list', request=request, format=format),
#             'products': drf_reverse('product-list', request=request, format=format),
#             'orders': drf_reverse('order-list', request=request, format=format),
#             'delivery-zones': drf_reverse('deliveryzone-list', request=request, format=format),
#             'delivery-persons': drf_reverse('deliveryperson-list', request=request, format=format),
#             'restaurants': drf_reverse('restaurant-list', request=request, format=format),
#             'delivery-tracking': drf_reverse('deliverytracking-list', request=request, format=format),
#             'order-items': drf_reverse('orderitem-list', request=request, format=format), # Добавлено
#             'ratings': drf_reverse('rating-list', request=request, format=format),       # Добавлено
#             'map': drf_reverse('map-data', request=request, format=format), # Изменено с map-list на map-data
#             'register': drf_reverse('register', request=request, format=format),
#             'api-token-auth': drf_reverse('token_obtain_pair', request=request, format=format), # JWT логин
#             'api-token-refresh': drf_reverse('token_refresh', request=request, format=format), # JWT refresh
#             'user-profile': drf_reverse('user-profile', request=request, format=format),
#         })
