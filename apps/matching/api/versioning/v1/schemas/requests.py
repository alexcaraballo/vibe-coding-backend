"""Request schemas for matching API."""
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, time
from typing import Optional


class CreateTravelRequestRequest(BaseModel):
    """Request para crear petición de viaje"""
    origin_address: str = Field(..., min_length=3, max_length=200)
    destination_address: str = Field(..., min_length=3, max_length=200)
    travel_date: date
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    seats_requested: int = Field(default=1, ge=1, le=10)
    passenger_notes: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_address": "Jerez de la Frontera, España",
                "destination_address": "Dos Hermanas, España",
                "travel_date": "2025-12-15",
                "time_from": "09:00:00",
                "time_to": "11:00:00",
                "seats_requested": 1
            }
        }
    )


class AcceptMatchRequest(BaseModel):
    """Request para aceptar un match"""
    trip_id: int = Field(..., description="ID del trayecto a reservar")
