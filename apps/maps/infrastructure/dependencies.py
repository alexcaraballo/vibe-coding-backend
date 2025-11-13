"""Dependency injection for maps module."""
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.services.map_service import MapService


async def get_map_service() -> IMapService:
    """Inyecta servicio de mapas"""
    return MapService()
