# Services package
from .routing import OSRMRoutingService, get_routing_service

# Alias for backward compatibility
GoogleDirectionsService = OSRMRoutingService
GeoapifyRoutingService = OSRMRoutingService

__all__ = ['OSRMRoutingService', 'GoogleDirectionsService', 'GeoapifyRoutingService', 'get_routing_service']
