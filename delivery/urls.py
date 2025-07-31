from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, ProductViewSet, DeliveryZoneViewSet, DeliveryPersonViewSet,
    OrderViewSet, OrderItemViewSet, DeliveryTrackingViewSet, RestaurantViewSet,
    RatingViewSet, home, map_view, UserProfileView, RegisterView, LoginView, MapViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'delivery-zones', DeliveryZoneViewSet)
router.register(r'delivery-persons', DeliveryPersonViewSet)
router.register(r'restaurants', RestaurantViewSet)
router.register(r'delivery-tracking', DeliveryTrackingViewSet)
router.register(r'map', MapViewSet, basename='map')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/login/', LoginView.as_view(), name='login'),
    path('api/user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('', home, name='home'),
    path('map/', map_view, name='map'),
]
