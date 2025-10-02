from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (  # Импортируем JWT views
    TokenObtainPairView, TokenRefreshView)
from django.views.generic import TemplateView

from .views import (
    ApiRoot, CategoryViewSet, DeliveryPersonViewSet, DeliveryTrackingViewSet,
    DeliveryZoneViewSet, DeviceTokenViewSet, MapViewSet, OrderItemViewSet,
    OrderViewSet, PaymentViewSet, PayoutViewSet, ProductViewSet, RatingViewSet,
    RegisterView, RestaurantViewSet, UserProfileView, MenuViewSet,
    CartViewSet,
    password_reset_request,
    password_reset_confirm,
    change_password,
    set_language_view,
    UserProfileViewSet
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet)
router.register(r"products", ProductViewSet)
router.register(r"menu/products", MenuViewSet, basename="menu-product")
router.register(r"menu/categories", CategoryViewSet, basename="menu-category")
router.register(r"orders", OrderViewSet, basename="order")
router.register(r"delivery-zones", DeliveryZoneViewSet)
router.register(r"delivery-persons", DeliveryPersonViewSet)
router.register(r"restaurants", RestaurantViewSet)
router.register(r"delivery-tracking", DeliveryTrackingViewSet)
router.register(r"order-items", OrderItemViewSet)
router.register(r"cart", CartViewSet, basename="cart")
router.register(r"ratings", RatingViewSet)
router.register(r"map", MapViewSet, basename="map")
router.register(r"payouts", PayoutViewSet, basename="payout")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(
    r"device-tokens", DeviceTokenViewSet, basename="device-token"
)  # Добавляем DeviceTokenViewSet
router.register(r'user-profiles', UserProfileViewSet)

urlpatterns = [
    path('', TemplateView.as_view(template_name='delivery/index.html'), name='home'),
    path(
        "", ApiRoot.as_view(), name="api-root"
    ),  # Добавляем ApiRoot как корневой маршрут для API
    path("endpoints/", include(router.urls)),
    path("register/", RegisterView.as_view(), name="register"),
    path("user-profile/", UserProfileView.as_view(), name="user-profile"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Password Reset URLs
    path(
        'password-reset-request/', 
        password_reset_request, 
        name='password_reset_request'
    ),
    path(
        'password-reset-confirm/', 
        password_reset_confirm, 
        name='password_reset_confirm'
    ),
    path(
        'change-password/', 
        change_password, 
        name='change_password'
    ),

    # Маршрут для смены языка
    path(
        'set-language/', 
        set_language_view, 
        name='set_language'
    ),
]
