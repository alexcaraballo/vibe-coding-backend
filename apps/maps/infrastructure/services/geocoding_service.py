"""Geocoding service using Nominatim (OpenStreetMap)."""
import httpx
from typing import Optional
from apps.maps.domain.models import Coordinates


class GeocodingService:
    """Servicio de geocodificación usando Nominatim (OpenStreetMap)"""

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(self):
        self.headers = {
            "User-Agent": "Vibe-Coding-Carpooling/1.0"  # Requerido por Nominatim
        }

    async def geocode(self, address: str) -> Optional[Coordinates]:
        """Convierte dirección a coordenadas"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "q": address,
                        "format": "json",
                        "limit": 1
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()

                data = response.json()
                if data and len(data) > 0:
                    return Coordinates(
                        latitude=float(data[0]["lat"]),
                        longitude=float(data[0]["lon"])
                    )
                return None
            except Exception as e:
                print(f"Error geocoding address: {e}")
                return None

    async def reverse_geocode(self, coordinates: Coordinates) -> Optional[str]:
        """Convierte coordenadas a dirección"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/reverse",
                    params={
                        "lat": coordinates.latitude,
                        "lon": coordinates.longitude,
                        "format": "json"
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                response.raise_for_status()

                data = response.json()
                return data.get("display_name")
            except Exception as e:
                print(f"Error reverse geocoding: {e}")
                return None
