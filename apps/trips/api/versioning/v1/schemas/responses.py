"""Response schemas for trips API."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date, time
from typing import Optional

from apps.users.api.versioning.v1.schemas.responses import UserResponse
from apps.trips.domain.models import VehicleType


class TripResponse(BaseModel):
    """Schema de respuesta de trayecto."""

    id: int
    origin: str
    destination: str
    departure_date: date
    departure_time: time
    available_seats: int
    total_seats: int
    driver_id: int
    status: str

    # Opcionales
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    estimated_arrival_time: Optional[time] = None
    max_detour_minutes: int
    current_detour_minutes: int
    price_per_seat: Optional[float] = None
    description: Optional[str] = None

    # CO₂ Impact (RF-BONUS-002)
    vehicle_type: VehicleType
    distance_km: Optional[float] = None
    co2_saved_per_passenger_kg: Optional[float] = None
    total_co2_saved_kg: Optional[float] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "total_seats": 3,
                "driver_id": 1,
                "status": "active",
                "max_detour_minutes": 30,
                "current_detour_minutes": 0,
                "price_per_seat": 5.0,
                "description": "Viaje tranquilo",
                "created_at": "2025-11-13T12:00:00",
                "updated_at": None
            }
        }
    )


class TripListResponse(BaseModel):
    """Schema de respuesta para lista de trayectos."""

    trips: list[TripResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trips": [
                    {
                        "id": 1,
                        "origin": "Cádiz",
                        "destination": "Sevilla",
                        "departure_date": "2025-12-15",
                        "departure_time": "09:00:00",
                        "available_seats": 3,
                        "total_seats": 3,
                        "driver_id": 1,
                        "status": "active",
                        "max_detour_minutes": 30,
                        "current_detour_minutes": 0,
                        "price_per_seat": 5.0,
                        "description": "Viaje tranquilo",
                        "created_at": "2025-11-13T12:00:00",
                        "updated_at": None
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 100
            }
        }
    )


class BookingResponse(BaseModel):
    """Schema de respuesta de reserva."""

    id: int
    trip_id: int
    passenger_id: int
    seats_booked: int
    status: str
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    passenger_notes: Optional[str] = None
    booking_date: datetime
    cancellation_date: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "trip_id": 1,
                "passenger_id": 2,
                "seats_booked": 1,
                "status": "confirmed",
                "passenger_notes": "Llegaré puntual",
                "booking_date": "2025-11-13T12:00:00",
                "cancellation_date": None,
                "is_active": True,
                "created_at": "2025-11-13T12:00:00",
                "updated_at": None
            }
        }
    )


class BookingWithTripResponse(BaseModel):
    """Schema de respuesta de reserva con información del trayecto y conductor."""

    booking: BookingResponse
    trip: TripResponse
    driver: Optional[UserResponse] = None  # Información del conductor

    model_config = ConfigDict(from_attributes=True)


class BookingListResponse(BaseModel):
    """Schema de respuesta para lista de reservas."""

    bookings: list[BookingResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bookings": [
                    {
                        "id": 1,
                        "trip_id": 1,
                        "passenger_id": 2,
                        "seats_booked": 1,
                        "status": "confirmed",
                        "passenger_notes": "Llegaré puntual",
                        "booking_date": "2025-11-13T12:00:00",
                        "is_active": True,
                        "created_at": "2025-11-13T12:00:00"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 100
            }
        }
    )


class CO2ImpactResponse(BaseModel):
    """Schema de respuesta del impacto de CO₂ de un trayecto."""

    trip_id: int
    vehicle_type: str
    distance_km: Optional[float]
    co2_saved_per_passenger_kg: Optional[float]
    total_co2_saved_kg: Optional[float]
    passengers_count: int
    equivalences: dict

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trip_id": 1,
                "vehicle_type": "gasoline",
                "distance_km": 120.5,
                "co2_saved_per_passenger_kg": 14.46,
                "total_co2_saved_kg": 28.92,
                "passengers_count": 2,
                "equivalences": {
                    "trees": "Equivalente a plantar 11.6 árboles por un año",
                    "km": "Equivalente a no conducir 144.6 km en coche convencional"
                }
            }
        }
    )


class UserCO2StatsResponse(BaseModel):
    """Schema de respuesta de estadísticas de CO₂ del usuario."""

    user_id: int
    total_co2_saved_kg: float
    trips_as_driver: int
    trips_as_passenger: int
    total_trips: int
    average_co2_per_trip_kg: float
    equivalence_trees: float
    equivalence_km_not_driven: float
    description: dict

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "total_co2_saved_kg": 156.80,
                "trips_as_driver": 5,
                "trips_as_passenger": 3,
                "total_trips": 8,
                "average_co2_per_trip_kg": 19.60,
                "equivalence_trees": 62.7,
                "equivalence_km_not_driven": 784.0,
                "description": {
                    "trees": "Equivalente a plantar 62.7 árboles por un año",
                    "km": "Equivalente a no conducir 784.0 km en coche convencional"
                }
            }
        }
    )
