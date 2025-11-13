"""Domain models for maps module."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class Coordinates(BaseModel):
    """Coordenadas geográficas"""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": 36.5271,
                "longitude": -6.2886
            }
        }
    )


class Location(BaseModel):
    """Ubicación con nombre y coordenadas"""

    name: str
    coordinates: Coordinates

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Cádiz, España",
                "coordinates": {
                    "latitude": 36.5271,
                    "longitude": -6.2886
                }
            }
        }
    )


class Route(BaseModel):
    """Ruta entre dos puntos"""

    origin: Location
    destination: Location
    distance_km: Optional[float] = None
    duration_minutes: Optional[int] = None
    polyline: Optional[list[Coordinates]] = Field(
        default=None,
        description="Lista de coordenadas que forman la ruta"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin": {
                    "name": "Cádiz",
                    "coordinates": {"latitude": 36.5271, "longitude": -6.2886}
                },
                "destination": {
                    "name": "Sevilla",
                    "coordinates": {"latitude": 37.3891, "longitude": -5.9845}
                },
                "distance_km": 125.5,
                "duration_minutes": 90
            }
        }
    )
