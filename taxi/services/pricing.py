# Расчёт стоимости поездки по тарифу (дистанция, время, базовая ставка)
import logging
from decimal import Decimal
from typing import Dict, Any, Optional

from taxi.models import Tariff
from taxi.services.routing import get_routing_service

logger = logging.getLogger(__name__)


class PriceCalculator:
    def __init__(self, tariff: Tariff):
        self.tariff = tariff

    def calculate_price(self, distance_km: float, duration_min: float) -> Decimal:
        distance = Decimal(str(distance_km))
        duration = Decimal(str(duration_min))
        
        price = (
            self.tariff.base_price +
            self.tariff.price_per_km * distance +
            self.tariff.price_per_min * duration
        )
        price = max(self.tariff.min_price, price)
        
        return price.quantize(Decimal('0.01'))
    
    def calculate_estimate(
        self,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float
    ) -> Dict[str, Any]:
        routing_service = get_routing_service()
        route_info = routing_service.get_route(
            start_lng=start_lng,
            start_lat=start_lat,
            end_lng=end_lng,
            end_lat=end_lat
        )
        
        distance_km = route_info['distance_km']
        duration_min = route_info['duration_min']
        price = self.calculate_price(distance_km, duration_min)

        result = {
            'distance_km': distance_km,
            'duration_min': duration_min,
            'price': float(price),
        }
        if route_info.get('geometry'):
            result['route_geometry'] = route_info['geometry']
        if route_info.get('is_estimate'):
            result['is_estimate'] = True
        
        return result


def calculate_trip_price(
    tariff_id: int,
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float
) -> Dict[str, Any]:
    tariff = Tariff.objects.get(id=tariff_id)
    calculator = PriceCalculator(tariff)
    return calculator.calculate_estimate(start_lat, start_lng, end_lat, end_lng)


def calculate_price_by_code(
    tariff_code: str,
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float
) -> Dict[str, Any]:
    tariff = Tariff.objects.get(code=tariff_code, is_active=True)
    calculator = PriceCalculator(tariff)
    return calculator.calculate_estimate(start_lat, start_lng, end_lat, end_lng)
