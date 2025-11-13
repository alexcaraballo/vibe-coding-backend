"""Booking repository implementation with SQLAlchemy."""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.exc import SQLAlchemyError

from apps.trips.domain.models import Booking
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.infrastructure.persistence.booking_models import BookingORM


class BookingRepository(IBookingRepository):
    """Implementación SQLAlchemy del repositorio de reservas."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, booking: Booking) -> Booking:
        """Create new booking in database."""
        try:
            booking_orm = BookingORM.from_domain(booking)
            self._session.add(booking_orm)
            await self._session.commit()
            await self._session.refresh(booking_orm)
            return booking_orm.to_domain()
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error creating booking: {str(e)}")

    async def get_by_id(self, booking_id: int) -> Optional[Booking]:
        """Get booking by ID."""
        try:
            result = await self._session.execute(
                select(BookingORM).where(BookingORM.id == booking_id)
            )
            booking_orm = result.scalar_one_or_none()
            return booking_orm.to_domain() if booking_orm else None
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting booking by id: {str(e)}")

    async def get_by_trip(
        self,
        trip_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Get all active bookings for a trip."""
        try:
            query = (
                select(BookingORM)
                .where(
                    BookingORM.trip_id == trip_id,
                    BookingORM.is_active == True
                )
                .offset(skip)
                .limit(limit)
                .order_by(BookingORM.booking_date.desc())
            )

            result = await self._session.execute(query)
            booking_orms = result.scalars().all()
            return [booking_orm.to_domain() for booking_orm in booking_orms]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting bookings by trip: {str(e)}")

    async def get_by_passenger(
        self,
        passenger_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Get all bookings for a passenger."""
        try:
            query = (
                select(BookingORM)
                .where(
                    BookingORM.passenger_id == passenger_id,
                    BookingORM.is_active == True
                )
                .offset(skip)
                .limit(limit)
                .order_by(BookingORM.booking_date.desc())
            )

            result = await self._session.execute(query)
            booking_orms = result.scalars().all()
            return [booking_orm.to_domain() for booking_orm in booking_orms]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting bookings by passenger: {str(e)}")

    async def exists_active_booking(
        self,
        trip_id: int,
        passenger_id: int
    ) -> bool:
        """Check if passenger has active booking for trip."""
        try:
            result = await self._session.execute(
                select(func.count())
                .select_from(BookingORM)
                .where(
                    and_(
                        BookingORM.trip_id == trip_id,
                        BookingORM.passenger_id == passenger_id,
                        BookingORM.is_active == True,
                        BookingORM.status.in_(["pending", "confirmed"])
                    )
                )
            )
            count = result.scalar()
            return count > 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error checking active booking: {str(e)}")

    async def update(self, booking_id: int, booking: Booking) -> bool:
        """Update booking."""
        try:
            result = await self._session.execute(
                select(BookingORM).where(BookingORM.id == booking_id)
            )
            booking_orm = result.scalar_one_or_none()

            if not booking_orm:
                return False

            # Update fields
            booking_orm.trip_id = booking.trip_id
            booking_orm.passenger_id = booking.passenger_id
            booking_orm.seats_booked = booking.seats_booked
            booking_orm.status = booking.status.value if hasattr(booking.status, 'value') else booking.status
            booking_orm.pickup_location = booking.pickup_location
            booking_orm.dropoff_location = booking.dropoff_location
            booking_orm.passenger_notes = booking.passenger_notes
            booking_orm.booking_date = booking.booking_date
            booking_orm.cancellation_date = booking.cancellation_date
            booking_orm.is_active = booking.is_active
            booking_orm.updated_at = datetime.utcnow()

            await self._session.commit()
            return True
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error updating booking: {str(e)}")

    async def delete(self, booking_id: int) -> bool:
        """Soft delete booking (set is_active=False, status=cancelled)."""
        try:
            result = await self._session.execute(
                select(BookingORM).where(BookingORM.id == booking_id)
            )
            booking_orm = result.scalar_one_or_none()

            if not booking_orm:
                return False

            booking_orm.is_active = False
            booking_orm.status = "cancelled"
            booking_orm.cancellation_date = datetime.utcnow()
            booking_orm.updated_at = datetime.utcnow()

            await self._session.commit()
            return True
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error deleting booking: {str(e)}")

    async def count_by_trip(self, trip_id: int) -> int:
        """Count active bookings for a trip."""
        try:
            result = await self._session.execute(
                select(func.count())
                .select_from(BookingORM)
                .where(
                    BookingORM.trip_id == trip_id,
                    BookingORM.is_active == True,
                    BookingORM.status.in_(["confirmed", "pending"])
                )
            )
            return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error counting bookings: {str(e)}")

    async def get_total_seats_booked(self, trip_id: int) -> int:
        """Sum total seats booked for a trip."""
        try:
            result = await self._session.execute(
                select(func.sum(BookingORM.seats_booked))
                .where(
                    BookingORM.trip_id == trip_id,
                    BookingORM.is_active == True,
                    BookingORM.status.in_(["confirmed", "pending"])
                )
            )
            total = result.scalar()
            return total if total is not None else 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting total seats booked: {str(e)}")
