"""SQLAlchemy ORM models for User persistence.

This module contains database representations separate from domain entities.
Uses SQLAlchemy 2.0 async patterns with Mapped type hints.
"""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from config.database import Base
from apps.users.domain.models import User, UserRole

if TYPE_CHECKING:
    from apps.trips.infrastructure.persistence.models import TripORM
    from apps.trips.infrastructure.persistence.booking_models import BookingORM
    from apps.matching.infrastructure.persistence.models import TravelRequestORM


class UserORM(Base):
    """
    SQLAlchemy ORM model for User table.

    This is the database representation, separate from domain entity.
    Uses SQLAlchemy 2.0 mapped_column syntax for async operations.
    """
    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Required Fields
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.PASSENGER.value)

    # Optional Fields
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Status Fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        onupdate=datetime.utcnow,
        nullable=True
    )

    # Driver-specific fields
    vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vehicle_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships (lazy loaded)
    travel_requests: Mapped[list["TravelRequestORM"]] = relationship(
        "TravelRequestORM",
        back_populates="passenger",
        foreign_keys="[TravelRequestORM.passenger_id]",
        lazy="noload"
    )

    def to_domain(self) -> User:
        """
        Convert ORM model to domain entity.

        This is the bridge between infrastructure and domain layers.
        """
        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            name=self.name,
            phone=self.phone,
            role=UserRole(self.role),
            is_active=self.is_active,
            is_verified=self.is_verified,
            created_at=self.created_at,
            updated_at=self.updated_at,
            vehicle_model=self.vehicle_model,
            vehicle_plate=self.vehicle_plate,
            license_number=self.license_number,
        )

    @staticmethod
    def from_domain(user: User) -> "UserORM":
        """
        Convert domain entity to ORM model.

        Used when creating/updating database records.
        """
        return UserORM(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            name=user.name,
            phone=user.phone,
            role=user.role.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            vehicle_model=user.vehicle_model,
            vehicle_plate=user.vehicle_plate,
            license_number=user.license_number,
        )

    def __repr__(self) -> str:
        return f"<UserORM(id={self.id}, email={self.email}, role={self.role})>"
