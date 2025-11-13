# Plan: RF-005 - Visualización de Rutas en Mapa

**Issue**: #5
**Prioridad**: MEDIA (MVP pero puede ser simplificada)
**Estimación**: 3-4 horas
**Dependencias**: 02-RF-001-publicacion-trayectos.md (completado)

---

## Objetivo

Permitir visualizar los trayectos en un mapa interactivo, mostrando la ruta entre origen y destino con marcadores claros y representación visual de la ruta.

---

## Análisis Previo

### Decisiones de Arquitectura

**Proveedor de Mapas Recomendado**: OpenStreetMap con Nominatim
- ✅ Gratuito y sin límites estrictos
- ✅ No requiere API key para uso básico
- ✅ Open source
- ❌ Menos features que Google Maps/Mapbox

**Alternativas**:
- **Mapbox**: Gratuito hasta 50k requests/mes, requiere API key
- **Google Maps**: Requiere API key y billing, más caro
- **Leaflet.js**: Librería frontend para renderizar mapas (se puede usar con cualquier proveedor)

### Arquitectura Objetivo
```
apps/maps/
├── domain/
│   ├── models.py              # Route, Coordinates
│   └── services/
│       └── map_service.py     # IMapService (interface)
├── infrastructure/
│   ├── dependencies.py        # DI para map service
│   └── services/
│       ├── map_service.py     # MapService (implementación)
│       └── geocoding_service.py # GeocodingService
└── api/
    ├── urls.py
    └── versioning/v1/
        ├── views.py           # Endpoints de mapas
        └── schemas/
            ├── requests.py    # RouteRequest
            └── responses.py   # RouteResponse
```

---

## Paso 1: Modelos de Dominio

**Archivo**: `apps/maps/domain/models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class Coordinates(BaseModel):
    """Coordenadas geográficas"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 36.5271,
                "longitude": -6.2886
            }
        }

class Location(BaseModel):
    """Ubicación con nombre y coordenadas"""
    name: str
    coordinates: Coordinates

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Cádiz, España",
                "coordinates": {
                    "latitude": 36.5271,
                    "longitude": -6.2886
                }
            }
        }

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

    class Config:
        json_schema_extra = {
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
```

---

## Paso 2: Interface del Servicio

**Archivo**: `apps/maps/domain/services/map_service.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.maps.domain.models import Coordinates, Location, Route

class IMapService(ABC):
    """Contrato para servicio de mapas"""

    @abstractmethod
    async def geocode(self, address: str) -> Optional[Coordinates]:
        """
        Convierte dirección a coordenadas (geocodificación).

        Args:
            address: Dirección textual (ej: "Cádiz, España")

        Returns:
            Coordinates o None si no se encontró
        """
        pass

    @abstractmethod
    async def reverse_geocode(self, coordinates: Coordinates) -> Optional[str]:
        """
        Convierte coordenadas a dirección (geocodificación inversa).

        Args:
            coordinates: Coordenadas geográficas

        Returns:
            Dirección textual o None
        """
        pass

    @abstractmethod
    async def get_route(
        self,
        origin: Coordinates,
        destination: Coordinates
    ) -> Optional[Route]:
        """
        Calcula ruta entre dos puntos.

        Args:
            origin: Coordenadas de origen
            destination: Coordenadas de destino

        Returns:
            Route con distancia, duración y polyline
        """
        pass
```

---

## Paso 3: Implementación con Nominatim (OpenStreetMap)

**Archivo**: `apps/maps/infrastructure/services/geocoding_service.py`

```python
import httpx
from typing import Optional
from apps.maps.domain.models import Coordinates, Location

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
```

**Archivo**: `apps/maps/infrastructure/services/map_service.py`

```python
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
```

---

## Paso 4: Dependency Injection

**Archivo**: `apps/maps/infrastructure/dependencies.py`

```python
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.services.map_service import MapService

async def get_map_service() -> IMapService:
    """Inyecta servicio de mapas"""
    return MapService()
```

---

## Paso 5: DTOs (Schemas)

**Archivo**: `apps/maps/api/versioning/v1/schemas/requests.py`

```python
from pydantic import BaseModel, Field
from typing import Optional

class GeocodeRequest(BaseModel):
    """Request para geocodificar dirección"""
    address: str = Field(..., min_length=3, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "address": "Cádiz, España"
            }
        }

class RouteRequest(BaseModel):
    """Request para calcular ruta"""
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    origin_lat: Optional[float] = Field(None, ge=-90, le=90)
    origin_lng: Optional[float] = Field(None, ge=-180, le=180)
    destination_lat: Optional[float] = Field(None, ge=-90, le=90)
    destination_lng: Optional[float] = Field(None, ge=-180, le=180)

    class Config:
        json_schema_extra = {
            "example": {
                "origin_address": "Cádiz, España",
                "destination_address": "Sevilla, España"
            }
        }
```

**Archivo**: `apps/maps/api/versioning/v1/schemas/responses.py`

```python
from pydantic import BaseModel
from typing import Optional
from apps.maps.domain.models import Coordinates, Location, Route

# Reutilizar modelos del dominio como respuestas
class CoordinatesResponse(Coordinates):
    """Response de coordenadas"""
    pass

class LocationResponse(Location):
    """Response de ubicación"""
    pass

class RouteResponse(Route):
    """Response de ruta"""
    pass
```

---

## Paso 6: Endpoints

**Archivo**: `apps/maps/api/versioning/v1/views.py`

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.maps.domain.models import Coordinates
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.dependencies import get_map_service
from apps.maps.api.versioning.v1.schemas.requests import GeocodeRequest, RouteRequest
from apps.maps.api.versioning.v1.schemas.responses import (
    CoordinatesResponse,
    LocationResponse,
    RouteResponse
)

# También necesitamos acceso a trips para obtener coordenadas
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_trip_repository

router = APIRouter()

@router.post("/geocode", response_model=CoordinatesResponse)
async def geocode_address(
    payload: GeocodeRequest,
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Geocodificar dirección (convertir a coordenadas).

    **Uso**: Convertir "Cádiz, España" a lat/lng
    """
    coordinates = await map_service.geocode(payload.address)

    if not coordinates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontraron coordenadas para: {payload.address}"
        )

    return CoordinatesResponse(**coordinates.model_dump())

@router.post("/route", response_model=RouteResponse)
async def calculate_route(
    payload: RouteRequest,
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Calcular ruta entre dos puntos.

    **Opciones:**
    1. Proporcionar direcciones (origin_address, destination_address)
    2. Proporcionar coordenadas (origin_lat/lng, destination_lat/lng)

    **Retorna:**
    - Ruta con polyline (lista de coordenadas)
    - Distancia en km
    - Duración estimada en minutos
    """
    # Geocodificar si se proporcionaron direcciones
    if payload.origin_address:
        origin_coords = await map_service.geocode(payload.origin_address)
        if not origin_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró origen: {payload.origin_address}"
            )
    elif payload.origin_lat and payload.origin_lng:
        origin_coords = Coordinates(
            latitude=payload.origin_lat,
            longitude=payload.origin_lng
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar origin_address o origin_lat/lng"
        )

    if payload.destination_address:
        dest_coords = await map_service.geocode(payload.destination_address)
        if not dest_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró destino: {payload.destination_address}"
            )
    elif payload.destination_lat and payload.destination_lng:
        dest_coords = Coordinates(
            latitude=payload.destination_lat,
            longitude=payload.destination_lng
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar destination_address o destination_lat/lng"
        )

    # Calcular ruta
    route = await map_service.get_route(origin_coords, dest_coords)

    if not route:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo calcular la ruta"
        )

    return RouteResponse(**route.model_dump())

@router.get("/trip/{trip_id}/route", response_model=RouteResponse)
async def get_trip_route(
    trip_id: str,
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Obtener ruta de un trayecto específico.

    **Endpoint principal para RF-005:**
    - Obtiene trayecto por ID
    - Calcula ruta entre origen y destino
    - Retorna información completa de la ruta
    """
    # Obtener trayecto
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trayecto no encontrado"
        )

    # Si el trayecto tiene coordenadas, usarlas directamente
    if (trip.origin_lat and trip.origin_lng and
        trip.destination_lat and trip.destination_lng):
        origin_coords = Coordinates(
            latitude=trip.origin_lat,
            longitude=trip.origin_lng
        )
        dest_coords = Coordinates(
            latitude=trip.destination_lat,
            longitude=trip.destination_lng
        )
    else:
        # Si no, geocodificar las direcciones
        origin_coords = await map_service.geocode(trip.origin)
        if not origin_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se pudo geocodificar origen: {trip.origin}"
            )

        dest_coords = await map_service.geocode(trip.destination)
        if not dest_coords:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se pudo geocodificar destino: {trip.destination}"
            )

        # Actualizar trip con coordenadas (para futuras consultas)
        trip.origin_lat = origin_coords.latitude
        trip.origin_lng = origin_coords.longitude
        trip.destination_lat = dest_coords.latitude
        trip.destination_lng = dest_coords.longitude
        await trip_repo.update(trip_id, trip)

    # Calcular ruta
    route = await map_service.get_route(origin_coords, dest_coords)

    if not route:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo calcular la ruta"
        )

    return RouteResponse(**route.model_dump())
```

---

## Paso 7: Registrar Router

**Archivo**: `apps/maps/api/urls.py`

```python
from fastapi import APIRouter
from apps.maps.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1", tags=["Maps"])
```

**Actualizar**: `main.py`

```python
from apps.maps.api.urls import router as maps_router

# En la sección de routers
app.include_router(maps_router, prefix="/api/v1/maps", tags=["Maps"])
```

---

## Paso 8: Frontend Simple (Opcional - para demo)

**Archivo**: `static/map-viewer.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Visualizador de Rutas</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        #map { height: 600px; width: 100%; }
    </style>
</head>
<body>
    <h1>Visualizador de Rutas - Carpooling</h1>
    <div>
        <label>Trip ID: <input type="text" id="tripId" placeholder="507f1f77bcf86cd799439011" /></label>
        <button onclick="loadRoute()">Cargar Ruta</button>
    </div>
    <div id="map"></div>

    <script>
        const map = L.map('map').setView([37.3891, -5.9845], 8);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        let routeLayer;

        async function loadRoute() {
            const tripId = document.getElementById('tripId').value;
            if (!tripId) {
                alert('Por favor ingresa un Trip ID');
                return;
            }

            try {
                const response = await fetch(`/api/v1/maps/v1/trip/${tripId}/route`);
                const route = await response.json();

                // Limpiar ruta anterior
                if (routeLayer) {
                    map.removeLayer(routeLayer);
                }

                // Crear polyline
                const latlngs = route.polyline.map(coord => [coord.latitude, coord.longitude]);
                routeLayer = L.polyline(latlngs, {color: 'blue', weight: 4}).addTo(map);

                // Marcadores
                L.marker([route.origin.coordinates.latitude, route.origin.coordinates.longitude])
                    .addTo(map)
                    .bindPopup(`<b>Origen:</b> ${route.origin.name}`);

                L.marker([route.destination.coordinates.latitude, route.destination.coordinates.longitude])
                    .addTo(map)
                    .bindPopup(`<b>Destino:</b> ${route.destination.name}`);

                // Ajustar vista
                map.fitBounds(routeLayer.getBounds());

                alert(`Ruta cargada: ${route.distance_km} km, ${route.duration_minutes} min`);
            } catch (error) {
                alert('Error cargando ruta: ' + error.message);
            }
        }
    </script>
</body>
</html>
```

Servir desde FastAPI:

```python
# main.py
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

---

## Paso 9: Testing

**Archivo**: `tests/test_maps/test_map_service.py`

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_geocode_address():
    """Test geocodificación"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/maps/v1/geocode",
            json={"address": "Cádiz, España"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "latitude" in data
    assert "longitude" in data
    # Verificar que las coordenadas están en el rango de Cádiz
    assert 36 <= data["latitude"] <= 37
    assert -7 <= data["longitude"] <= -6

@pytest.mark.asyncio
async def test_calculate_route():
    """Test cálculo de ruta"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/maps/v1/route",
            json={
                "origin_address": "Cádiz, España",
                "destination_address": "Sevilla, España"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "origin" in data
    assert "destination" in data
    assert "distance_km" in data
    assert "duration_minutes" in data
    assert "polyline" in data
    assert data["distance_km"] > 0

@pytest.mark.asyncio
async def test_get_trip_route(trip_id):
    """Test obtener ruta de trayecto"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/maps/v1/trip/{trip_id}/route")

    assert response.status_code == 200
    data = response.json()
    assert "polyline" in data
    assert len(data["polyline"]) > 0
```

---

## Checklist de Implementación

- [ ] Crear estructura de carpetas para módulo maps
- [ ] Modelos de dominio: Coordinates, Location, Route
- [ ] Interface IMapService
- [ ] GeocodingService (Nominatim)
- [ ] MapService (OSRM para routing)
- [ ] Dependency injection
- [ ] Schemas de request/response
- [ ] Endpoints:
  - [ ] POST /geocode (dirección → coordenadas)
  - [ ] POST /route (calcular ruta)
  - [ ] GET /trip/{id}/route (ruta de trayecto)
- [ ] Router registrado en main.py
- [ ] (Opcional) HTML viewer con Leaflet.js
- [ ] Tests de integración
- [ ] Verificar en /docs

---

## Verificación

```bash
# Geocodificar dirección
curl -X POST http://localhost:8000/api/v1/maps/v1/geocode \
  -H "Content-Type: application/json" \
  -d '{"address": "Cádiz, España"}'

# Calcular ruta
curl -X POST http://localhost:8000/api/v1/maps/v1/route \
  -H "Content-Type: application/json" \
  -d '{
    "origin_address": "Cádiz, España",
    "destination_address": "Sevilla, España"
  }'

# Obtener ruta de trayecto
curl http://localhost:8000/api/v1/maps/v1/trip/<TRIP_ID>/route

# Ver mapa interactivo (si implementaste el HTML)
open http://localhost:8000/static/map-viewer.html
```

---

## Criterios de Aceptación (de Issue #5)

✅ Usuario puede solicitar "Ver en mapa" desde cualquier trayecto
✅ Sistema muestra mapa con la ruta visualizada
✅ Marcadores claros para origen y destino
✅ Ruta dibujada como línea/polilínea entre puntos
✅ Mapa tiene nivel de zoom apropiado
✅ Funciona sin autenticación (público)
✅ Integración funcional con servicio de mapas (OpenStreetMap)

---

## Notas Importantes

**Limitaciones de Nominatim:**
- Rate limit: 1 request/segundo
- Requiere User-Agent en headers
- No apto para producción de alto tráfico (considerar caché)

**Mejoras Futuras:**
- Implementar caché de geocodificación (Redis)
- Considerar Mapbox/Google Maps para producción
- Agregar waypoints intermedios en el roadmap
- Visualización del roadmap dinámico (RF-006)

---

## Próximo Paso

Una vez completado RF-005, proceder con:
- **RF-006**: Motor de Matching Avanzado (requisito más complejo)
