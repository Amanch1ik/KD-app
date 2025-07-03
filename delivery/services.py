import requests
from django.conf import settings
from typing import Dict, Any, Tuple, List

class DGISService:
    """Сервис для работы с API 2ГИС"""
    
    BASE_URL = "https://api.2gis.com/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.DGIS_API_KEY
    
    def calculate_route(
        self,
        points: List[Tuple[float, float]],
        vehicle_type: str = "car"
    ) -> Dict[str, Any]:
        """
        Рассчитывает маршрут между точками
        
        Args:
            points: Список точек в формате [(lat1, lon1), (lat2, lon2), ...]
            vehicle_type: Тип транспортного средства (car, bicycle, foot)
            
        Returns:
            Dict с информацией о маршруте
        """
        if len(points) < 2:
            raise ValueError("Необходимо минимум 2 точки для построения маршрута")
            
        url = f"{self.BASE_URL}/routing"
        
        # Формируем строку с точками маршрута
        points_str = "|".join([f"{lon},{lat}" for lat, lon in points])
        
        params = {
            "key": self.api_key,
            "points": points_str,
            "type": vehicle_type,
            "output": "json"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        vehicle_type: str = "car"
    ) -> Dict[str, Any]:
        """
        Получает матрицу расстояний между точками
        
        Args:
            origins: Список начальных точек [(lat1, lon1), ...]
            destinations: Список конечных точек [(lat1, lon1), ...]
            vehicle_type: Тип транспортного средства
            
        Returns:
            Dict с матрицей расстояний
        """
        url = f"{self.BASE_URL}/matrix"
        
        # Формируем строки с точками
        origins_str = "|".join([f"{lon},{lat}" for lat, lon in origins])
        destinations_str = "|".join([f"{lon},{lat}" for lat, lon in destinations])
        
        params = {
            "key": self.api_key,
            "origins": origins_str,
            "destinations": destinations_str,
            "type": vehicle_type,
            "output": "json"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def calculate_delivery_cost(
        self,
        distance_meters: float,
        base_rate: float = 80.0,
        rate_per_km: float = 20.0,
        min_cost: float = 80.0
    ) -> float:
        """
        Рассчитывает стоимость доставки на основе расстояния
        
        Args:
            distance_meters: Расстояние в метрах
            base_rate: Базовая ставка
            rate_per_km: Ставка за километр
            min_cost: Минимальная стоимость
            
        Returns:
            float: Стоимость доставки
        """
        distance_km = distance_meters / 1000
        cost = base_rate + (distance_km * rate_per_km)
        return max(cost, min_cost) 