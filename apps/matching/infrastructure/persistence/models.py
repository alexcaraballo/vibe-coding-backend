"""SQLAlchemy ORM models for matching module."""
from sqlalchemy import Column, Integer, String, Float, Date, Time, DateTime, Boolean, ForeignKey, Enum as SQLAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date, time
from typing import Optional

from config.database import Base
from apps.matching.domain.models import TravelRequestStatus


class TravelRequestORM(Base):
    """Modelo ORM para TravelRequest (petición de viaje)"""
    __tablename__ = "travel_requests"

    # Identificador
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Pasajero
    passenger_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Ubicaciones (coordenadas)
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)
    destination_lat: Mapped[float] = mapped_column(Float, nullable=False)
    destination_lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Direcciones textuales (opcional)
    origin_address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    destination_address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Criterios temporales
    travel_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_from: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    time_to: Mapped[Optional[time]] = mapped_column(Time, nullable=True)

    # Detalles
    seats_requested: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    passenger_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Estado
    status: Mapped[str] = mapped_column(
        String(20),
        default=TravelRequestStatus.PENDING.value,
        nullable=False,
        index=True
    )
    matched_trip_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True)

    # Metadatos
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    passenger: Mapped["UserORM"] = relationship("UserORM", back_populates="travel_requests", foreign_keys=[passenger_id])
    matched_trip: Mapped[Optional["TripORM"]] = relationship("TripORM", foreign_keys=[matched_trip_id])

    def __repr__(self):
        return f"<TravelRequestORM(id={self.id}, passenger_id={self.passenger_id}, status={self.status})>"
