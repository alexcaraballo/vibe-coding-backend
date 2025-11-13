"""
SQLAlchemy models for users module.
Infrastructure layer - Database representations.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from config.database import Base
import enum


class UserRole(str, enum.Enum):
    """User role enum"""
    DRIVER = "driver"
    PASSENGER = "passenger"
    BOTH = "both"


class UserModel(Base):
    """
    SQLAlchemy model for User entity.

    Represents users in the carpooling system, both drivers and passengers.
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile Information
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)

    # Role
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.PASSENGER)

    # Driver Information (optional, only for drivers)
    vehicle_model = Column(String(100), nullable=True)
    vehicle_plate = Column(String(20), nullable=True)
    license_number = Column(String(50), nullable=True)

    # Privacy Settings
    profile_photo_url = Column(String(500), nullable=True)
    bio = Column(String(500), nullable=True)
    show_email_to_fellow_travelers = Column(Boolean, default=False)
    show_phone_to_fellow_travelers = Column(Boolean, default=False)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    # Trips where this user is the driver
    trips_as_driver = relationship(
        "TripModel",
        back_populates="driver",
        foreign_keys="TripModel.driver_id",
        cascade="all, delete-orphan"
    )

    # Bookings where this user is the passenger
    bookings_as_passenger = relationship(
        "BookingModel",
        back_populates="passenger",
        foreign_keys="BookingModel.passenger_id",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}', role='{self.role}')>"
