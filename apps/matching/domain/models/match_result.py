"""Match result domain models."""
from pydantic import BaseModel, Field
from datetime import time
from typing import Optional


class WaypointInsertion(BaseModel):
    """Representa la inserción de waypoints en el roadmap"""
    pickup_index: int = Field(..., description="Índice donde insertar pickup")
    dropoff_index: int = Field(..., description="Índice donde insertar dropoff")
    pickup_location: dict = Field(..., description="Coordenadas de recogida")
    dropoff_location: dict = Field(..., description="Coordenadas de bajada")
    additional_detour_minutes: int = Field(..., description="Desvío adicional estimado")


class MatchScore(BaseModel):
    """Puntuación de compatibilidad de un match"""
    trip_id: int
    score: float = Field(..., ge=0, le=100, description="Puntuación 0-100")
    detour_additional: int = Field(..., description="Desvío adicional en minutos")
    proximity_score: float = Field(..., description="Proximidad geográfica")
    time_compatibility_score: float = Field(..., description="Compatibilidad temporal")


class MatchResult(BaseModel):
    """
    Resultado de evaluación de matching.
    Indica si un trayecto puede acomodar la petición.
    """
    trip_id: int
    is_compatible: bool
    reason: Optional[str] = None  # Razón si NO es compatible

    # Información del trayecto
    trip_origin: str
    trip_destination: str
    departure_time: time
    available_seats: int

    # Análisis de desvío
    current_detour_minutes: int
    max_detour_minutes: int
    additional_detour_minutes: Optional[int] = None
    projected_total_detour: Optional[int] = None

    # Inserción propuesta
    proposed_insertion: Optional[WaypointInsertion] = None

    # Puntuación
    match_score: Optional[MatchScore] = None

    # Información del conductor
    driver_id: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "trip_id": 1,
                "is_compatible": True,
                "trip_origin": "Cádiz",
                "trip_destination": "Sevilla",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "current_detour_minutes": 0,
                "max_detour_minutes": 30,
                "additional_detour_minutes": 20,
                "projected_total_detour": 20,
                "match_score": {
                    "trip_id": 1,
                    "score": 85.5,
                    "detour_additional": 20,
                    "proximity_score": 90.0,
                    "time_compatibility_score": 95.0
                }
            }
        }
