# Маршрут и дистанция через OSRM (OpenStreetMap) или Haversine
import logging
import math
from typing import Dict, Any, Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OSRMRoutingService:
    """Routing service using OSRM (Open Source Routing Machine) with OpenStreetMap data."""
    BASE_URL = "https://router.project-osrm.org/route/v1/driving"

    def __init__(self, api_key: Optional[str] = None):
        # OSRM is free and doesn't require an API key
        self.api_key = None
    
    def get_route(self, start_lng: float, start_lat: float,
                  end_lng: float, end_lat: float) -> Dict[str, Any]:
        try:
            # OSRM format: lng,lat
            origin = f"{start_lng},{start_lat}"
            destination = f"{end_lng},{end_lat}"
            url = f"{self.BASE_URL}/{origin};{destination}?overview=false"
            
            logger.info(f"Calling OSRM Routing API")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_route_response(data)

        except requests.exceptions.RequestException as e:
            logger.error(f"OSRM API request failed: {str(e)}")
            return self._calculate_haversine(start_lng, start_lat, end_lng, end_lat)
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse OSRM response: {str(e)}")
            return self._calculate_haversine(start_lng, start_lat, end_lng, end_lat)

    def _parse_route_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            code = data.get('code')
            if code != 'Ok':
                raise ValueError(f"OSRM API returned code: {code}")
            
            routes = data.get('routes', [])
            if not routes:
                raise ValueError("No routes found in response")
            
            route = routes[0]
            
            # OSRM returns distance in meters, duration in seconds
            distance_km = route.get('distance', 0) / 1000
            duration_min = route.get('duration', 0) / 60
            
            return {
                'distance_km': round(distance_km, 2),
                'duration_min': round(duration_min, 2),
                'geometry': None,  # OSRM geometry is encoded polyline if overview=full
                'is_estimate': False,
            }
            
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing route response: {str(e)}")
            raise ValueError(f"Invalid route response format: {str(e)}")
    
    def _calculate_haversine(self, start_lng: float, start_lat: float,
                            end_lng: float, end_lat: float) -> Dict[str, Any]:
        """Дистанция по формуле Haversine, если API недоступен."""
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
        # OSRM is always available (free public instance)
        return True


def get_routing_service() -> OSRMRoutingService:
    return OSRMRoutingService()
