"""Domain models for matching module."""
from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional
from enum import Enum


class TravelRequestStatus(str, Enum):
    """Estados de una petición de viaje"""
    PENDING = "pending"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class TravelRequest:
    """
    Petición de viaje de un pasajero.
    El motor de matching evalúa qué trayectos pueden acomodar esta petición.
    """
    # Identificador
    id: Optional[int] = None

    # Pasajero
    passenger_id: int = 0

    # Ubicaciones (coordenadas)
    origin_lat: float = 0.0
    origin_lng: float = 0.0
    destination_lat: float = 0.0
    destination_lng: float = 0.0

    # Direcciones textuales (opcional)
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None

    # Criterios temporales
    travel_date: Optional[date] = None
    time_from: Optional[time] = None  # "A partir de esta hora"
    time_to: Optional[time] = None    # "Antes de esta hora"

    # Detalles
    seats_requested: int = 1
    passenger_notes: Optional[str] = None

    # Estado
    status: TravelRequestStatus = TravelRequestStatus.PENDING
    matched_trip_id: Optional[int] = None

    # Metadatos
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validaciones post-init"""
        if not (-90 <= self.origin_lat <= 90):
            raise ValueError("origin_lat must be between -90 and 90")
        if not (-180 <= self.origin_lng <= 180):
            raise ValueError("origin_lng must be between -180 and 180")
        if not (-90 <= self.destination_lat <= 90):
            raise ValueError("destination_lat must be between -90 and 90")
        if not (-180 <= self.destination_lng <= 180):
            raise ValueError("destination_lng must be between -180 and 180")
        if not (1 <= self.seats_requested <= 10):
            raise ValueError("seats_requested must be between 1 and 10")
