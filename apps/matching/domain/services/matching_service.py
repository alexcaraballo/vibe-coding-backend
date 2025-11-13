"""Matching service interface."""
from abc import ABC, abstractmethod
from typing import Optional
from apps.matching.domain.models import TravelRequest, MatchResult


class IMatchingService(ABC):
    """Contrato para el servicio de matching"""

    @abstractmethod
    async def find_compatible_trips(
        self,
        travel_request: TravelRequest
    ) -> list[MatchResult]:
        """
        Encuentra trayectos compatibles para una petición de viaje.

        Returns:
            Lista de MatchResult ordenados por score (mejor primero)
        """
        pass

    @abstractmethod
    async def evaluate_compatibility(
        self,
        travel_request: TravelRequest,
        trip_id: int
    ) -> Optional[MatchResult]:
        """
        Evalúa si un trayecto específico es compatible.

        Returns:
            MatchResult con análisis detallado
        """
        pass

    @abstractmethod
    async def accept_match(
        self,
        travel_request_id: int,
        trip_id: int,
        passenger_id: int
    ) -> bool:
        """
        Acepta un match: crea booking y actualiza trip roadmap.

        Returns:
            True si se aceptó exitosamente
        """
        pass
