"""Request schemas for maps API."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class GeocodeRequest(BaseModel):
    """Request para geocodificar dirección"""

    address: str = Field(..., min_length=3, max_length=500)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "address": "Cádiz, España"
            }
        }
    )


class RouteRequest(BaseModel):
    """Request para calcular ruta"""

    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    origin_lat: Optional[float] = Field(None, ge=-90, le=90)
    origin_lng: Optional[float] = Field(None, ge=-180, le=180)
    destination_lat: Optional[float] = Field(None, ge=-90, le=90)
    destination_lng: Optional[float] = Field(None, ge=-180, le=180)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_address": "Cádiz, España",
                "destination_address": "Sevilla, España"
            }
        }
    )
