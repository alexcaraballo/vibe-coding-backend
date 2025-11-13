"""Booking ORM models with SQLAlchemy 2.0."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base
from apps.trips.domain.models import Booking, BookingStatus


class BookingORM(Base):
    """
    SQLAlchemy ORM model for bookings table.
    Maps between database and domain Booking entity.
    """
    __tablename__ = "bookings"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    trip_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    passenger_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Booking details
    seats_booked: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="confirmed",
        index=True
    )

    # Additional info
    pickup_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    dropoff_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    passenger_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    booking_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    cancellation_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    def to_domain(self) -> Booking:
        """Convert ORM model to domain entity."""
        return Booking(
            id=self.id,
            trip_id=self.trip_id,
            passenger_id=self.passenger_id,
            seats_booked=self.seats_booked,
            status=BookingStatus(self.status),
            pickup_location=self.pickup_location,
            dropoff_location=self.dropoff_location,
            passenger_notes=self.passenger_notes,
            booking_date=self.booking_date,
            cancellation_date=self.cancellation_date,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_domain(booking: Booking) -> "BookingORM":
        """Convert domain entity to ORM model."""
        return BookingORM(
            id=booking.id,
            trip_id=booking.trip_id,
            passenger_id=booking.passenger_id,
            seats_booked=booking.seats_booked,
            status=booking.status.value if hasattr(booking.status, 'value') else booking.status,
            pickup_location=booking.pickup_location,
            dropoff_location=booking.dropoff_location,
            passenger_notes=booking.passenger_notes,
            booking_date=booking.booking_date,
            cancellation_date=booking.cancellation_date,
            is_active=booking.is_active,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        )
