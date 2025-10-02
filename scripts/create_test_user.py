#!/usr/bin/env python
import os, sys, traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karakoldelivery.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

username = 'tuser_auto'
email = 'tuser_auto@example.com'
password = 'TestPass123'

try:
    print('User model:', User)
    user, created = User.objects.get_or_create(username=username, defaults={'email': email})
    if created:
        user.set_password(password)
        user.save()
        print('Created user id:', user.id)
    else:
        print('User exists id:', user.id)

    # Получаем JWT токены через сериализатор
    try:
        serializer = TokenObtainPairSerializer(data={'username': username, 'password': password})
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data
        print('Tokens:', tokens)
    except Exception as e:
        print('Token obtain failed:')
        traceback.print_exc()

except Exception:
    traceback.print_exc()
    sys.exit(1)


