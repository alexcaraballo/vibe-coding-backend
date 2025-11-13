"""Trip repository implementation with SQLAlchemy."""
from typing import Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.exc import SQLAlchemyError

from apps.trips.domain.models import Trip
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.persistence.models import TripORM


class TripRepository(ITripRepository):
    """Implementación SQLAlchemy del repositorio de trayectos."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, trip: Trip) -> Trip:
        """Create new trip in database."""
        try:
            trip_orm = TripORM.from_domain(trip)
            self._session.add(trip_orm)
            await self._session.commit()
            await self._session.refresh(trip_orm)
            return trip_orm.to_domain()
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error creating trip: {str(e)}")

    async def get_by_id(self, trip_id: int) -> Optional[Trip]:
        """Get trip by ID."""
        try:
            result = await self._session.execute(
                select(TripORM).where(TripORM.id == trip_id)
            )
            trip_orm = result.scalar_one_or_none()
            return trip_orm.to_domain() if trip_orm else None
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting trip by id: {str(e)}")

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> list[Trip]:
        """List all trips with pagination and optional status filter."""
        try:
            query = select(TripORM)

            if status:
                query = query.where(TripORM.status == status)

            query = query.offset(skip).limit(limit).order_by(TripORM.departure_date.desc())

            result = await self._session.execute(query)
            trip_orms = result.scalars().all()
            return [trip_orm.to_domain() for trip_orm in trip_orms]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting all trips: {str(e)}")

    async def get_by_driver(
        self,
        driver_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """Get all trips by driver."""
        try:
            query = (
                select(TripORM)
                .where(TripORM.driver_id == driver_id)
                .offset(skip)
                .limit(limit)
                .order_by(TripORM.departure_date.desc())
            )

            result = await self._session.execute(query)
            trip_orms = result.scalars().all()
            return [trip_orm.to_domain() for trip_orm in trip_orms]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting trips by driver: {str(e)}")

    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """
        Search trips by criteria (for RF-002).

        - Case-insensitive search on origin/destination
        - Only active trips with available seats
        - By default, only future trips (date >= today)
        - Ordered by departure date (nearest first)
        """
        try:
            from datetime import date as dt_date

            query = select(TripORM).where(
                TripORM.status == "active",
                TripORM.is_active == True,
                TripORM.available_seats > 0  # Only trips with available seats
            )

            # Case-insensitive search on origin
            if origin:
                query = query.where(TripORM.origin.ilike(f"%{origin}%"))

            # Case-insensitive search on destination
            if destination:
                query = query.where(TripORM.destination.ilike(f"%{destination}%"))

            # Filter by date (default: only future trips)
            if date_from:
                query = query.where(TripORM.departure_date >= date_from)
            else:
                # By default, only future trips
                query = query.where(TripORM.departure_date >= dt_date.today())

            # Order by date (nearest first) and paginate
            query = query.order_by(TripORM.departure_date.asc()).offset(skip).limit(limit)

            result = await self._session.execute(query)
            trip_orms = result.scalars().all()
            return [trip_orm.to_domain() for trip_orm in trip_orms]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error searching trips: {str(e)}")

    async def update(self, trip_id: int, trip: Trip) -> bool:
        """Update trip."""
        try:
            result = await self._session.execute(
                select(TripORM).where(TripORM.id == trip_id)
            )
            trip_orm = result.scalar_one_or_none()

            if not trip_orm:
                return False

            # Update fields
            trip_orm.origin = trip.origin
            trip_orm.destination = trip.destination
            trip_orm.departure_date = trip.departure_date
            trip_orm.departure_time = trip.departure_time
            trip_orm.origin_lat = trip.origin_lat
            trip_orm.origin_lng = trip.origin_lng
            trip_orm.destination_lat = trip.destination_lat
            trip_orm.destination_lng = trip.destination_lng
            trip_orm.available_seats = trip.available_seats
            trip_orm.total_seats = trip.total_seats
            trip_orm.estimated_arrival_time = trip.estimated_arrival_time
            trip_orm.max_detour_minutes = trip.max_detour_minutes
            trip_orm.current_detour_minutes = trip.current_detour_minutes
            trip_orm.driver_id = trip.driver_id
            trip_orm.status = trip.status.value if hasattr(trip.status, 'value') else trip.status
            trip_orm.price_per_seat = trip.price_per_seat
            trip_orm.description = trip.description
            trip_orm.is_active = trip.is_active
            trip_orm.updated_at = datetime.utcnow()

            await self._session.commit()
            return True
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error updating trip: {str(e)}")

    async def delete(self, trip_id: int) -> bool:
        """Soft delete trip (set is_active=False, status=cancelled)."""
        try:
            result = await self._session.execute(
                select(TripORM).where(TripORM.id == trip_id)
            )
            trip_orm = result.scalar_one_or_none()

            if not trip_orm:
                return False

            trip_orm.is_active = False
            trip_orm.status = "cancelled"
            trip_orm.updated_at = datetime.utcnow()

            await self._session.commit()
            return True
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error deleting trip: {str(e)}")

    async def exists(self, trip_id: int) -> bool:
        """Check if trip exists."""
        try:
            result = await self._session.execute(
                select(func.count()).select_from(TripORM).where(TripORM.id == trip_id)
            )
            count = result.scalar()
            return count > 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error checking trip existence: {str(e)}")

    async def count_active(self) -> int:
        """Count active trips."""
        try:
            result = await self._session.execute(
                select(func.count()).select_from(TripORM).where(
                    TripORM.status == "active",
                    TripORM.is_active == True
                )
            )
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error counting active trips: {str(e)}")
