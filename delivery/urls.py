from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'delivery-zones', views.DeliveryZoneViewSet)
router.register(r'delivery-persons', views.DeliveryPersonViewSet)
router.register(r'restaurants', views.RestaurantViewSet)
router.register(r'delivery-tracking', views.DeliveryTrackingViewSet)
router.register(r'map', views.MapViewSet, basename='map')

urlpatterns = [
    path('', views.home, name='home'),
    path('map/', views.map_view, name='map'),
    path('api/', include(router.urls)),
]
