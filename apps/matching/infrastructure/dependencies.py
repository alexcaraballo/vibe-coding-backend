"""Dependency injection for matching module."""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.infrastructure.repositories.travel_request_repository import TravelRequestRepository
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.infrastructure.services.matching_service import MatchingService
from apps.trips.infrastructure.dependencies import get_trip_repository, get_booking_repository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository


async def get_travel_request_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> ITravelRequestRepository:
    """Inyecta repositorio de travel requests"""
    return TravelRequestRepository(session)


async def get_matching_service(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
) -> IMatchingService:
    """Inyecta servicio de matching"""
    return MatchingService(trip_repo, booking_repo, travel_request_repo)
