"""Booking repository interface (contract)."""
from abc import ABC, abstractmethod
from typing import Optional
from apps.trips.domain.models import Booking


class IBookingRepository(ABC):
    """Contrato para el repositorio de reservas."""

    @abstractmethod
    async def create(self, booking: Booking) -> Booking:
        """
        Crea una nueva reserva.
        Retorna la reserva con id asignado.
        """
        pass

    @abstractmethod
    async def get_by_id(self, booking_id: int) -> Optional[Booking]:
        """Obtiene reserva por ID."""
        pass

    @abstractmethod
    async def get_by_trip(
        self,
        trip_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Obtiene todas las reservas activas de un trayecto."""
        pass

    @abstractmethod
    async def get_by_passenger(
        self,
        passenger_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Obtiene todas las reservas de un pasajero."""
        pass

    @abstractmethod
    async def exists_active_booking(
        self,
        trip_id: int,
        passenger_id: int
    ) -> bool:
        """Verifica si el pasajero ya tiene una reserva activa en el trayecto."""
        pass

    @abstractmethod
    async def update(self, booking_id: int, booking: Booking) -> bool:
        """
        Actualiza reserva.
        Retorna True si actualizó correctamente.
        """
        pass

    @abstractmethod
    async def delete(self, booking_id: int) -> bool:
        """Elimina reserva (soft delete)."""
        pass

    @abstractmethod
    async def count_by_trip(self, trip_id: int) -> int:
        """Cuenta reservas activas de un trayecto."""
        pass

    @abstractmethod
    async def get_total_seats_booked(self, trip_id: int) -> int:
        """Suma total de plazas reservadas en un trayecto."""
        pass
