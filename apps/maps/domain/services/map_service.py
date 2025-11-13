"""Map service interface."""
from abc import ABC, abstractmethod
from typing import Optional
from apps.maps.domain.models import Coordinates, Route


class IMapService(ABC):
    """Contrato para servicio de mapas"""

    @abstractmethod
    async def geocode(self, address: str) -> Optional[Coordinates]:
        """
        Convierte dirección a coordenadas (geocodificación).

        Args:
            address: Dirección textual (ej: "Cádiz, España")

        Returns:
            Coordinates o None si no se encontró
        """
        pass

    @abstractmethod
    async def reverse_geocode(self, coordinates: Coordinates) -> Optional[str]:
        """
        Convierte coordenadas a dirección (geocodificación inversa).

        Args:
            coordinates: Coordenadas geográficas

        Returns:
            Dirección textual o None
        """
        pass

    @abstractmethod
    async def get_route(
        self,
        origin: Coordinates,
        destination: Coordinates
    ) -> Optional[Route]:
        """
        Calcula ruta entre dos puntos.

        Args:
            origin: Coordenadas de origen
            destination: Coordenadas de destino

        Returns:
            Route con distancia, duración y polyline
        """
        pass
