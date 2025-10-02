from django.contrib.auth import get_user_model
User = get_user_model()
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, DeliveryPerson, UserProfile, Rating, DeliveryZone
# Временно отключаем сложные сигналы
# from .services import DGISService
# from firebase_admin import messaging
import logging
from django.db.models import Avg

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Автоматическое создание профиля пользователя при регистрации
    
    Используем get_or_create, чтобы не создавать дубликаты профиля при повторной регистрации
    (например, во время миграций или повторных сигналов).
    """
    from .models import UserProfile
    
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Сохранение профиля пользователя
    """
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=DeliveryPerson)
def update_delivery_person_profile(sender, instance, **kwargs):
    user_profile, created = UserProfile.objects.get_or_create(user=instance.user)
    user_profile.role = "courier"
    user_profile.phone_number = instance.phone_number
    user_profile.save()


@receiver(pre_save, sender=Order)
def calculate_order_fees(sender, instance, **kwargs):
    if instance.pk:  # Only calculate fees for existing orders, not new ones (cart status)
        if instance.status != 'cart':
            # Attempt to calculate distance via 2GIS
            distance_meters = None
            try:
                if instance.restaurant and instance.delivery_latitude and instance.delivery_longitude:
                    # dgis = DGISService() # Временно отключаем DGIS
                    # matrix = dgis.get_distance_matrix( # Временно отключаем DGIS
                    #     origins=[(instance.restaurant.latitude, instance.restaurant.longitude)],
                    #     destinations=[
                    #         (float(instance.delivery_latitude), float(instance.delivery_longitude))
                    #     ],
                    # )
                    # distance_meters = matrix["routes"][0]["distance"]  # in meters # Временно отключаем DGIS
                    pass # Временно отключаем DGIS
            except Exception as e:
                logger.warning(
                    f"Error calculating distance via 2GIS: {e}."
                    " Using fixed rate."
                )
                distance_meters = None

            if distance_meters:
                # delivery_fee = DGISService().calculate_delivery_cost(distance_meters) # Временно отключаем DGIS
                pass # Временно отключаем DGIS
            else:
                # Fallback logic (as before)
                zone_fee = instance.delivery_zone.delivery_fee if instance.delivery_zone else 100
                percent_fee = instance.total_amount * 0.10  # 10%
                min_fee = 80
                delivery_fee = max(zone_fee, percent_fee, min_fee)

            # 4. Service fee (e.g., 15% of delivery cost)
            service_fee = delivery_fee * 0.15
            # 5. Courier payment (the rest)
            courier_fee = delivery_fee - service_fee
            instance.delivery_fee = delivery_fee
            instance.service_fee = service_fee
            instance.courier_fee = courier_fee
    else:
        # Для новых заказов (cart) не пересчитываем total_amount здесь.
        # Разрешаем caller устанавливать total_amount явно при создании.
        pass


@receiver(post_save, sender=Rating)
def update_aggregates_on_rating_save(sender, instance, **kwargs):
    # update aggregates
    # courier average
    courier_avg = instance.courier.ratings.aggregate(avg=Avg("score"))["avg"] or 0
    instance.courier.avg_rating = courier_avg
    instance.courier.save(update_fields=["avg_rating"])
    # restaurant average
    rest_avg = instance.restaurant.ratings.aggregate(avg=Avg("score"))["avg"] or 0
    instance.restaurant.avg_rating = rest_avg
    instance.restaurant.save(update_fields=["avg_rating"])

    # DeliveryZone average
    if instance.order.delivery_zone:
        zone_avg = (
            Order.objects.filter(
                delivery_zone=instance.order.delivery_zone, status="delivered"
            ).aggregate(avg=Avg("rating__score"))["avg"]
            or 0
        )
        instance.order.delivery_zone.avg_rating = zone_avg
        instance.order.delivery_zone.save(update_fields=["avg_rating"])
