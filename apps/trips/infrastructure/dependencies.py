"""Dependency injection for trips module."""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.services.co2_service import ICO2Service
from apps.trips.infrastructure.repositories.trip_repository import TripRepository
from apps.trips.infrastructure.repositories.booking_repository import BookingRepository
from apps.trips.infrastructure.services.booking_service import BookingService
from apps.trips.infrastructure.services.co2_calculator import CO2Calculator
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.dependencies import get_map_service


async def get_trip_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> ITripRepository:
    """
    Inyecta repositorio de trayectos.

    Args:
        session: SQLAlchemy async session

    Returns:
        ITripRepository implementation
    """
    return TripRepository(session)


async def get_booking_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> IBookingRepository:
    """
    Inyecta repositorio de reservas.

    Args:
        session: SQLAlchemy async session

    Returns:
        IBookingRepository implementation
    """
    return BookingRepository(session)


async def get_booking_service(
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
) -> BookingService:
    """
    Inyecta servicio de reservas.

    Args:
        booking_repo: Repository de reservas
        trip_repo: Repository de trayectos

    Returns:
        BookingService instance
    """
    return BookingService(booking_repo, trip_repo)


async def get_co2_service(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    map_service: Annotated[IMapService, Depends(get_map_service)]
) -> ICO2Service:
    """
    Inyecta servicio de cálculo de CO₂.

    Args:
        trip_repo: Repository de trayectos
        booking_repo: Repository de reservas
        map_service: Servicio de mapas

    Returns:
        ICO2Service instance
    """
    return CO2Calculator(trip_repo, booking_repo, map_service)
