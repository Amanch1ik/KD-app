from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, DeliveryPerson

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    # else: # Необязательно, если профиль всегда создается при создании пользователя
    #     instance.profile.save() # Можно обновить профиль, если изменились поля пользователя

@receiver(post_save, sender=DeliveryPerson)
def update_delivery_person_profile(sender, instance, **kwargs):
    user_profile, created = UserProfile.objects.get_or_create(user=instance.user)
    user_profile.role = 'courier'
    user_profile.phone_number = instance.phone_number
    user_profile.save()
