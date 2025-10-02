import os
import django

# Ensure Django settings are configured before tests import models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "karakoldelivery.settings_dev")
os.environ.setdefault("SECRET_KEY", "dev-key-for-tests-001")
django.setup()


