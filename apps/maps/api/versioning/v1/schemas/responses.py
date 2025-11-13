"""Response schemas for maps API."""
from apps.maps.domain.models import Coordinates, Location, Route


# Reutilizar modelos del dominio como respuestas
class CoordinatesResponse(Coordinates):
    """Response de coordenadas"""
    pass


class LocationResponse(Location):
    """Response de ubicación"""
    pass


class RouteResponse(Route):
    """Response de ruta"""
    pass
