from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.utils import timezone
from datetime import timedelta

from .models import Order, DeliveryPerson, Restaurant, Product


class QueryOptimizer:
    """
    Класс для оптимизации запросов к базе данных
    """

    @staticmethod
    def get_active_orders(user=None, days=7):
        """
        Получение активных заказов с оптимизацией запросов
        
        :param user: Пользователь (необязательно)
        :param days: Количество дней для выборки заказов
        :return: QuerySet активных заказов
        """
        # Кэшируем результат на 5 минут
        cache_key = f"active_orders_{user.id if user else 'all'}_{days}"
        cached_orders = cache.get(cache_key)
        
        if cached_orders is not None:
            return cached_orders

        # Базовый фильтр по давности заказов
        time_threshold = timezone.now() - timedelta(days=days)
        
        # Базовый запрос с жадной загрузкой связанных моделей
        query = Order.objects.filter(
            created_at__gte=time_threshold
        ).select_related(
            'customer', 
            'delivery_person', 
            'restaurant'
        ).prefetch_related(
            Prefetch('items', queryset=Product.objects.select_related('category'))
        )

        # Фильтрация по пользователю, если указан
        if user:
            if user.is_staff:
                query = query
            elif hasattr(user, 'deliveryperson'):
                # Для курьера - его заказы и доступные
                query = query.filter(
                    Q(delivery_person=user.deliveryperson) | 
                    Q(status__in=['pending', 'confirmed'], delivery_person__isnull=True)
                )
            else:
                # Для обычного пользователя - только его заказы
                query = query.filter(customer=user)

        # Оптимизация сортировки
        query = query.order_by('-created_at')

        # Кэширование результата
        cache.set(cache_key, query, timeout=300)  # 5 минут
        
        return query

    @staticmethod
    def get_available_couriers(radius=None, vehicle_type=None):
        """
        Получение доступных курьеров с фильтрацией
        
        :param radius: Радиус поиска (км)
        :param vehicle_type: Тип транспорта
        :return: QuerySet доступных курьеров
        """
        cache_key = f"available_couriers_{radius}_{vehicle_type}"
        cached_couriers = cache.get(cache_key)
        
        if cached_couriers is not None:
            return cached_couriers

        # Базовый запрос доступных курьеров
        query = DeliveryPerson.objects.filter(
            is_available=True, 
            status='available'
        ).select_related('user')

        # Фильтрация по типу транспорта
        if vehicle_type:
            query = query.filter(vehicle_type=vehicle_type)

        # TODO: Реализовать фильтрацию по радиусу, когда будут координаты

        # Кэширование результата
        cache.set(cache_key, query, timeout=300)  # 5 минут
        
        return query

    @staticmethod
    def get_restaurant_menu(restaurant_id):
        """
        Получение меню ресторана с оптимизацией
        
        :param restaurant_id: ID ресторана
        :return: QuerySet продуктов ресторана
        """
        cache_key = f"restaurant_menu_{restaurant_id}"
        cached_menu = cache.get(cache_key)
        
        if cached_menu is not None:
            return cached_menu

        # Получаем меню с жадной загрузкой связей
        menu = Product.objects.filter(
            restaurant_id=restaurant_id, 
            is_available=True
        ).select_related(
            'category', 
            'restaurant'
        ).order_by('category__name', 'name')

        # Кэширование результата
        cache.set(cache_key, menu, timeout=1800)  # 30 минут
        
        return menu
