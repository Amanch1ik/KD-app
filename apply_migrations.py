import os
import sys
import django
from django.conf import settings
from django.core.management import call_command

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karakoldelivery.settings')
django.setup()

def apply_migrations():
    try:
        # Применяем миграции
        call_command('migrate', 'delivery', verbosity=2)
        print("Миграции успешно применены!")
    except Exception as e:
        print(f"Ошибка при применении миграций: {e}")

if __name__ == '__main__':
    apply_migrations()
