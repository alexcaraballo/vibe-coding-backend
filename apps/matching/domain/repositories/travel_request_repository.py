"""Travel request repository interface."""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import date
from apps.matching.domain.models import TravelRequest


class ITravelRequestRepository(ABC):
    """Contrato para el repositorio de peticiones de viaje"""

    @abstractmethod
    async def create(self, travel_request: TravelRequest) -> TravelRequest:
        """Crea una nueva petición de viaje"""
        pass

    @abstractmethod
    async def get_by_id(self, request_id: int) -> Optional[TravelRequest]:
        """Obtiene petición por ID"""
        pass

    @abstractmethod
    async def get_by_passenger(
        self,
        passenger_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[TravelRequest]:
        """Obtiene peticiones de un pasajero"""
        pass

    @abstractmethod
    async def get_pending_by_date(self, travel_date: date) -> list[TravelRequest]:
        """Obtiene peticiones pendientes para una fecha específica"""
        pass

    @abstractmethod
    async def update(self, request_id: int, travel_request: TravelRequest) -> bool:
        """Actualiza petición"""
        pass

    @abstractmethod
    async def delete(self, request_id: int) -> bool:
        """Elimina petición"""
        pass
