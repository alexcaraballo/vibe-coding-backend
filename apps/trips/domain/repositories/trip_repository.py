"""Trip repository interface (contract)."""
from abc import ABC, abstractmethod
from typing import Optional
from datetime import date
from apps.trips.domain.models import Trip


class ITripRepository(ABC):
    """Contrato para el repositorio de trayectos."""

    @abstractmethod
    async def create(self, trip: Trip) -> Trip:
        """
        Crea un nuevo trayecto. Retorna el trayecto con id asignado.

        Args:
            trip: Entidad Trip a crear

        Returns:
            Trip con ID asignado
        """
        pass

    @abstractmethod
    async def get_by_id(self, trip_id: int) -> Optional[Trip]:
        """
        Obtiene trayecto por ID.

        Args:
            trip_id: ID del trayecto

        Returns:
            Trip si existe, None si no
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> list[Trip]:
        """
        Lista trayectos con paginación y filtro opcional por estado.

        Args:
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar
            status: Filtro opcional por estado

        Returns:
            Lista de trayectos
        """
        pass

    @abstractmethod
    async def get_by_driver(
        self,
        driver_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """
        Obtiene todos los trayectos de un conductor.

        Args:
            driver_id: ID del conductor
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar

        Returns:
            Lista de trayectos del conductor
        """
        pass

    @abstractmethod
    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """
        Busca trayectos por criterios (para RF-002).

        Args:
            origin: Filtro por origen (búsqueda parcial)
            destination: Filtro por destino (búsqueda parcial)
            date_from: Filtro por fecha mínima
            skip: Número de registros a saltar
            limit: Número máximo de registros a retornar

        Returns:
            Lista de trayectos que coinciden con los criterios
        """
        pass

    @abstractmethod
    async def update(self, trip_id: int, trip: Trip) -> bool:
        """
        Actualiza trayecto. Retorna True si actualizó.

        Args:
            trip_id: ID del trayecto a actualizar
            trip: Entidad Trip con datos actualizados

        Returns:
            True si se actualizó, False si no
        """
        pass

    @abstractmethod
    async def delete(self, trip_id: int) -> bool:
        """
        Elimina trayecto (soft delete: is_active=False).

        Args:
            trip_id: ID del trayecto a eliminar

        Returns:
            True si se eliminó, False si no
        """
        pass

    @abstractmethod
    async def exists(self, trip_id: int) -> bool:
        """
        Verifica si un trayecto existe.

        Args:
            trip_id: ID del trayecto

        Returns:
            True si existe, False si no
        """
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """
        Cuenta el número de trayectos activos.

        Returns:
            Número total de trayectos activos
        """
        pass
