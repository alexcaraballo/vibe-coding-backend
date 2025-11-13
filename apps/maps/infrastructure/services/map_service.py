"""Map service implementation with OpenStreetMap."""
import httpx
from typing import Optional
from apps.maps.domain.models import Coordinates, Location, Route
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.services.geocoding_service import GeocodingService


class MapService(IMapService):
    """Implementación de servicio de mapas con OpenStreetMap"""

    def __init__(self):
        self.geocoding_service = GeocodingService()
        self.routing_base_url = "https://router.project-osrm.org"

    async def geocode(self, address: str) -> Optional[Coordinates]:
        """Geocodificación usando Nominatim"""
        return await self.geocoding_service.geocode(address)

    async def reverse_geocode(self, coordinates: Coordinates) -> Optional[str]:
        """Geocodificación inversa"""
        return await self.geocoding_service.reverse_geocode(coordinates)

    async def get_route(
        self,
        origin: Coordinates,
        destination: Coordinates
    ) -> Optional[Route]:
        """
        Calcula ruta usando OSRM (Open Source Routing Machine).

        OSRM es un servicio gratuito de routing sobre OpenStreetMap.
        """
        async with httpx.AsyncClient() as client:
            try:
                # Formato: /route/v1/{profile}/{coordinates}
                # profile: car, bike, foot
                url = (
                    f"{self.routing_base_url}/route/v1/driving/"
                    f"{origin.longitude},{origin.latitude};"
                    f"{destination.longitude},{destination.latitude}"
                )

                response = await client.get(
                    url,
                    params={
                        "overview": "full",
                        "geometries": "geojson"
                    },
                    timeout=10.0
                )
                response.raise_for_status()

                data = response.json()

                if data.get("code") != "Ok" or not data.get("routes"):
                    return None

                route_data = data["routes"][0]

                # Extraer polyline
                geometry = route_data.get("geometry", {})
                coordinates_list = geometry.get("coordinates", [])
                polyline = [
                    Coordinates(latitude=coord[1], longitude=coord[0])
                    for coord in coordinates_list
                ]

                # Obtener nombres de ubicaciones
                origin_name = await self.reverse_geocode(origin) or "Origen"
                dest_name = await self.reverse_geocode(destination) or "Destino"

                return Route(
                    origin=Location(name=origin_name, coordinates=origin),
                    destination=Location(name=dest_name, coordinates=destination),
                    distance_km=round(route_data.get("distance", 0) / 1000, 2),
                    duration_minutes=round(route_data.get("duration", 0) / 60),
                    polyline=polyline
                )

            except Exception as e:
                print(f"Error calculating route: {e}")
                return None
