"""Request schemas for trips API."""
from pydantic import BaseModel, Field
from datetime import date, time
from typing import Optional
from apps.trips.domain.models import VehicleType


class CreateTripRequest(BaseModel):
    """Schema para crear trayecto."""

    origin: str = Field(..., min_length=3, max_length=200, description="Ciudad o ubicación de origen")
    destination: str = Field(..., min_length=3, max_length=200, description="Ciudad o ubicación de destino")
    departure_date: date = Field(..., description="Fecha del viaje (YYYY-MM-DD)")
    departure_time: time = Field(..., description="Hora de salida (HH:MM:SS)")
    available_seats: int = Field(..., ge=1, le=10, description="Plazas disponibles")

    # Opcionales
    price_per_seat: Optional[float] = Field(None, ge=0, description="Precio por plaza en euros")
    description: Optional[str] = Field(None, max_length=500, description="Descripción del viaje")
    max_detour_minutes: int = Field(default=30, ge=0, le=120, description="Desvío máximo permitido en minutos")
    estimated_arrival_time: Optional[time] = Field(None, description="Hora estimada de llegada")

    # CO₂ calculation (RF-BONUS-002)
    vehicle_type: VehicleType = Field(default=VehicleType.GASOLINE, description="Tipo de vehículo para cálculo de CO₂")

    # Geographic coordinates (optional)
    origin_lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud del origen")
    origin_lng: Optional[float] = Field(None, ge=-180, le=180, description="Longitud del origen")
    destination_lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud del destino")
    destination_lng: Optional[float] = Field(None, ge=-180, le=180, description="Longitud del destino")

    model_config = {
        "json_schema_extra": {
            "example": {
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "price_per_seat": 5.0,
                "description": "Viaje tranquilo, acepto mascotas",
                "max_detour_minutes": 30
            }
        }
    }


class UpdateTripRequest(BaseModel):
    """Schema para actualizar trayecto (todos los campos opcionales para partial update)."""

    available_seats: Optional[int] = Field(None, ge=0, le=10, description="Plazas disponibles")
    price_per_seat: Optional[float] = Field(None, ge=0, description="Precio por plaza")
    description: Optional[str] = Field(None, max_length=500, description="Descripción")
    status: Optional[str] = Field(None, description="Estado del trayecto (active, completed, cancelled)")
    max_detour_minutes: Optional[int] = Field(None, ge=0, le=120, description="Desvío máximo en minutos")

    model_config = {
        "json_schema_extra": {
            "example": {
                "available_seats": 2,
                "price_per_seat": 6.0,
                "description": "Actualización: salida a las 09:15"
            }
        }
    }


class BookTripRequest(BaseModel):
    """Schema para reservar trayecto."""

    seats_requested: int = Field(default=1, ge=1, le=10, description="Número de plazas a reservar")
    passenger_notes: Optional[str] = Field(None, max_length=500, description="Notas adicionales del pasajero")
    pickup_location: Optional[str] = Field(None, max_length=200, description="Punto de recogida específico")
    dropoff_location: Optional[str] = Field(None, max_length=200, description="Punto de bajada específico")

    # Geographic coordinates (RF-BONUS-003)
    pickup_lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud del punto de recogida")
    pickup_lng: Optional[float] = Field(None, ge=-180, le=180, description="Longitud del punto de recogida")
    dropoff_lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitud del punto de bajada")
    dropoff_lng: Optional[float] = Field(None, ge=-180, le=180, description="Longitud del punto de bajada")

    model_config = {
        "json_schema_extra": {
            "example": {
                "seats_requested": 1,
                "passenger_notes": "Llegaré 5 minutos antes",
                "pickup_location": "Estación de tren de Cádiz",
                "pickup_lat": 36.5297,
                "pickup_lng": -6.2926
            }
        }
    }


class SendChatMessageRequest(BaseModel):
    """Schema para enviar mensaje de chat (RF-BONUS-004)."""

    message: str = Field(..., min_length=1, max_length=1000, description="Contenido del mensaje")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Hola, ¿a qué hora pasas a recogerme?"
            }
        }
    }
