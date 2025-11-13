"""
SQLAlchemy models for trips module.
Infrastructure layer - Database representations.
"""
from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Time, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from config.database import Base
import enum


class TripStatus(str, enum.Enum):
    """Trip status enum"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BookingStatus(str, enum.Enum):
    """Booking status enum"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class VehicleType(str, enum.Enum):
    """Vehicle type enum for CO2 calculations"""
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"


class TripModel(Base):
    """
    SQLAlchemy model for Trip entity.

    Represents a trip/journey published by a driver.
    """
    __tablename__ = "trips"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Location Information
    origin = Column(String(255), nullable=False, index=True)
    destination = Column(String(255), nullable=False, index=True)

    # GPS Coordinates
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)

    # Date and Time
    departure_date = Column(Date, nullable=False, index=True)
    departure_time = Column(Time, nullable=False)

    # Seats
    available_seats = Column(Integer, nullable=False)
    total_seats = Column(Integer, nullable=False)

    # Driver (Foreign Key to User)
    driver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Pricing
    price_per_seat = Column(Float, nullable=False)

    # Description and Notes
    description = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(TripStatus), default=TripStatus.ACTIVE, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Matching Configuration
    max_detour_minutes = Column(Integer, default=30, nullable=False)
    max_pickup_deviation_km = Column(Float, default=10.0, nullable=False)
    max_dropoff_deviation_km = Column(Float, default=10.0, nullable=False)

    # Vehicle Information
    vehicle_type = Column(SQLEnum(VehicleType), default=VehicleType.GASOLINE, nullable=False)
    vehicle_model = Column(String(100), nullable=True)
    vehicle_plate = Column(String(20), nullable=True)

    # Environmental Metrics
    distance_km = Column(Float, nullable=True)
    co2_saved_per_passenger_kg = Column(Float, nullable=True)
    total_co2_saved_kg = Column(Float, default=0.0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    driver = relationship(
        "UserModel",
        back_populates="trips_as_driver",
        foreign_keys=[driver_id]
    )

    bookings = relationship(
        "BookingModel",
        back_populates="trip",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Trip(id={self.id}, origin='{self.origin}', destination='{self.destination}', date={self.departure_date})>"


class BookingModel(Base):
    """
    SQLAlchemy model for Booking entity.

    Represents a passenger's reservation for a trip.
    """
    __tablename__ = "bookings"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign Keys
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    passenger_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Booking Details
    seats_booked = Column(Integer, nullable=False, default=1)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING, nullable=False, index=True)

    # Pickup and Dropoff
    pickup_location = Column(String(255), nullable=True)
    dropoff_location = Column(String(255), nullable=True)

    # Notes
    passenger_notes = Column(Text, nullable=True)
    driver_notes = Column(Text, nullable=True)

    # Status Flags
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship(
        "TripModel",
        back_populates="bookings",
        foreign_keys=[trip_id]
    )

    passenger = relationship(
        "UserModel",
        back_populates="bookings_as_passenger",
        foreign_keys=[passenger_id]
    )

    def __repr__(self):
        return f"<Booking(id={self.id}, trip_id={self.trip_id}, passenger_id={self.passenger_id}, seats={self.seats_booked}, status='{self.status}')>"
