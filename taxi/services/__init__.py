# Services package
from .routing import GoogleDirectionsService, get_routing_service

# Alias for backward compatibility
GeoapifyRoutingService = GoogleDirectionsService

__all__ = ['GoogleDirectionsService', 'GeoapifyRoutingService', 'get_routing_service']
