#!/usr/bin/env python
import os
import sys
from pathlib import Path
import django
import json
import traceback

# Ensure project root is on sys.path so `karakoldelivery` package can be imported
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karakoldelivery.settings')
django.setup()

from delivery.models import Product
from delivery.serializers import ProductSerializer

def main():
    try:
        qs = Product.objects.filter(is_available=True)[:10]
        print('Products count:', qs.count())
        ser = ProductSerializer(qs, many=True)
        print('Serialized OK. Sample JSON:')
        print(json.dumps(ser.data[:3], ensure_ascii=False, indent=2))
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()


