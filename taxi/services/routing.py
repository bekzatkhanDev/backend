# Маршрут и дистанция через Google Directions или Haversine
import logging
import math
from typing import Dict, Any, Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GoogleDirectionsService:
    BASE_URL = "https://maps.googleapis.com/maps/api/directions/json"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'GOOGLE_API_KEY', None)
        if not self.api_key:
            logger.warning("Google API key not configured")
    
    def get_route(self, start_lng: float, start_lat: float,
                  end_lng: float, end_lat: float) -> Dict[str, Any]:
        if not self.api_key:
            return self._calculate_haversine(start_lng, start_lat, end_lng, end_lat)

        try:
            origin = f"{start_lat},{start_lng}"
            destination = f"{end_lat},{end_lng}"
            url = f"{self.BASE_URL}?origin={origin}&destination={destination}&mode=driving&key={self.api_key}"
            
            logger.info(f"Calling Google Directions API")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_route_response(data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Google Directions API request failed: {str(e)}")
            return self._calculate_haversine(start_lng, start_lat, end_lng, end_lat)
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Google Directions response: {str(e)}")
            return self._calculate_haversine(start_lng, start_lat, end_lng, end_lat)

    def _parse_route_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            status = data.get('status')
            if status != 'OK':
                raise ValueError(f"Google API returned status: {status}")
            
            routes = data.get('routes', [])
            if not routes:
                raise ValueError("No routes found in response")
            
            legs = routes[0].get('legs', [])
            if not legs:
                raise ValueError("No legs found in route")
            
            leg = legs[0]
            
            distance = leg.get('distance', {})
            distance_km = distance.get('value', 0) / 1000
            
            duration = leg.get('duration', {})
            duration_min = duration.get('value', 0) / 60
            
            geometry = None
            overview_polyline = routes[0].get('overview_polyline', {})
            if overview_polyline:
                geometry = overview_polyline.get('points')
            
            return {
                'distance_km': round(distance_km, 2),
                'duration_min': round(duration_min, 2),
                'geometry': geometry,
            }
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing route response: {str(e)}")
            raise ValueError(f"Invalid route response format: {str(e)}")
    
    def _calculate_haversine(self, start_lng: float, start_lat: float,
                            end_lng: float, end_lat: float) -> Dict[str, Any]:
        """Дистанция по формуле Haversine, если нет ключа Google."""
        R = 6371.0
        lat1 = math.radians(start_lat)
        lat2 = math.radians(end_lat)
        lng1 = math.radians(start_lng)
        lng2 = math.radians(end_lng)
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = R * c
        avg_speed_kmh = 30
        duration_min = (distance_km / avg_speed_kmh) * 60
        logger.info(f"Using Haversine fallback: {distance_km:.2f} km, {duration_min:.2f} min")
        return {
            'distance_km': round(distance_km, 2),
            'duration_min': round(duration_min, 2),
            'geometry': None,
            'is_estimate': True,
        }

    def is_configured(self) -> bool:
        return bool(self.api_key)


def get_routing_service() -> GoogleDirectionsService:
    api_key = getattr(settings, 'GOOGLE_API_KEY', None)
    return GoogleDirectionsService(api_key=api_key)
