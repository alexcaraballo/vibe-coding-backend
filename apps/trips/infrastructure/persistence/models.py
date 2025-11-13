"""SQLAlchemy ORM models for trips module."""
from sqlalchemy import Boolean, DateTime, Integer, String, Float, Date, Time, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date, time
from typing import Optional

from config.database import Base
from apps.trips.domain.models import Trip, TripStatus, VehicleType


class TripORM(Base):
    """SQLAlchemy ORM model for Trip table (SQLAlchemy 2.0 style)."""
    __tablename__ = "trips"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic trip information
    origin: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Geographic coordinates (for matching)
    origin_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    origin_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    destination_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    destination_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Seat management
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)

    # Matching engine fields (RF-006)
    estimated_arrival_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    max_detour_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    current_detour_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # CO₂ Impact fields (RF-BONUS-002)
    vehicle_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VehicleType.GASOLINE.value
    )
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    co2_saved_per_passenger_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_co2_saved_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Driver (foreign key to users table)
    driver_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Metadata
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TripStatus.ACTIVE.value,
        index=True
    )
    price_per_seat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    def to_domain(self) -> Trip:
        """
        Convert ORM model to domain entity.

        Returns:
            Trip domain entity
        """
        return Trip(
            id=self.id,
            origin=self.origin,
            destination=self.destination,
            departure_date=self.departure_date,
            departure_time=self.departure_time,
            origin_lat=self.origin_lat,
            origin_lng=self.origin_lng,
            destination_lat=self.destination_lat,
            destination_lng=self.destination_lng,
            available_seats=self.available_seats,
            total_seats=self.total_seats,
            estimated_arrival_time=self.estimated_arrival_time,
            max_detour_minutes=self.max_detour_minutes,
            current_detour_minutes=self.current_detour_minutes,
            vehicle_type=VehicleType(self.vehicle_type),
            distance_km=self.distance_km,
            co2_saved_per_passenger_kg=self.co2_saved_per_passenger_kg,
            total_co2_saved_kg=self.total_co2_saved_kg,
            driver_id=self.driver_id,
            status=TripStatus(self.status),
            price_per_seat=self.price_per_seat,
            description=self.description,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_domain(trip: Trip) -> "TripORM":
        """
        Convert domain entity to ORM model.

        Args:
            trip: Trip domain entity

        Returns:
            TripORM model
        """
        return TripORM(
            id=trip.id,
            origin=trip.origin,
            destination=trip.destination,
            departure_date=trip.departure_date,
            departure_time=trip.departure_time,
            origin_lat=trip.origin_lat,
            origin_lng=trip.origin_lng,
            destination_lat=trip.destination_lat,
            destination_lng=trip.destination_lng,
            available_seats=trip.available_seats,
            total_seats=trip.total_seats,
            estimated_arrival_time=trip.estimated_arrival_time,
            max_detour_minutes=trip.max_detour_minutes,
            current_detour_minutes=trip.current_detour_minutes,
            vehicle_type=trip.vehicle_type.value if isinstance(trip.vehicle_type, VehicleType) else trip.vehicle_type,
            distance_km=trip.distance_km,
            co2_saved_per_passenger_kg=trip.co2_saved_per_passenger_kg,
            total_co2_saved_kg=trip.total_co2_saved_kg,
            driver_id=trip.driver_id,
            status=trip.status.value if isinstance(trip.status, TripStatus) else trip.status,
            price_per_seat=trip.price_per_seat,
            description=trip.description,
            is_active=trip.is_active,
            created_at=trip.created_at,
            updated_at=trip.updated_at
        )
