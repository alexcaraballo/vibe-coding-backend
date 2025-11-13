# Plan: RF-BONUS-001 - Matching Aproximado Geográfico

**Issue**: #10
**Prioridad**: BAJA (Bonus - Mejora del matching básico)
**Estimación**: 3-4 horas
**Dependencias**:
- 07-RF-006-matching-avanzado.md (completado)
- 06-RF-005-visualizacion-mapas.md (completado - usa geocoding)

---

## Objetivo

Mejorar el motor de matching geográfico utilizando geocodificación y cálculo de distancias reales en lugar de coincidencias exactas de nombres de ciudad, permitiendo matches más precisos y flexibles.

---

## Análisis Previo

### Mejora sobre RF-006

**RF-006 actual** usa:
- `is_point_near_segment()` con threshold fijo de 15 km
- Comparación simplificada de distancias a extremos del segmento

**RF-BONUS-001** mejora con:
- Geocodificación automática de direcciones
- Cálculo de distancia perpendicular real al segmento de ruta
- Umbrales configurables por conductor
- Búsqueda por radio geográfico

### Conceptos Clave

**1. Distancia Perpendicular a Segmento**
- Proyección del punto sobre la línea del segmento
- Cálculo preciso usando fórmula de distancia punto-línea
- Más preciso que promedio de distancias a extremos

**2. Búsqueda por Radio**
- Permitir búsquedas "todos los viajes cerca de mi ubicación"
- Útil para descubrimiento de rutas alternativas

**3. Geocodificación Automática**
- Convertir todas las direcciones a coordenadas al crear trayecto
- Almacenar coordenadas en Trip para cálculos rápidos

### Arquitectura Objetivo
```
apps/matching/infrastructure/services/
├── geometric_matching_service.py  # Mejora del matching geográfico
└── distance_calculator.py         # Cálculos geométricos avanzados
```

---

## Paso 1: Servicio de Cálculo Geométrico Avanzado

**Archivo**: `apps/matching/infrastructure/services/distance_calculator.py`

```python
import math
from typing import Tuple
from apps.maps.domain.models import Coordinates

class DistanceCalculator:
    """
    Servicio avanzado de cálculos geométricos para matching.
    Mejora sobre DetourCalculator con algoritmos más precisos.
    """

    @staticmethod
    def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        """
        Distancia haversine entre dos puntos (en km).
        Reutiliza de DetourCalculator.
        """
        R = 6371  # Radio de la Tierra en km

        lat1 = math.radians(coord1.latitude)
        lat2 = math.radians(coord2.latitude)
        dlat = math.radians(coord2.latitude - coord1.latitude)
        dlon = math.radians(coord2.longitude - coord1.longitude)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    @staticmethod
    def point_to_segment_distance(
        point: Coordinates,
        segment_start: Coordinates,
        segment_end: Coordinates
    ) -> float:
        """
        Calcula la distancia perpendicular de un punto a un segmento de línea.

        Usa proyección del punto sobre el segmento:
        1. Si proyección está dentro del segmento: distancia perpendicular
        2. Si está fuera: distancia al extremo más cercano

        Returns:
            Distancia en kilómetros
        """
        # Convertir a coordenadas cartesianas aproximadas (válido para distancias cortas)
        # En producción, usar proyección esférica precisa

        # Punto P
        px = point.longitude
        py = point.latitude

        # Segmento A-B
        ax = segment_start.longitude
        ay = segment_start.latitude
        bx = segment_end.longitude
        by = segment_end.latitude

        # Vector AB
        ab_x = bx - ax
        ab_y = by - ay

        # Vector AP
        ap_x = px - ax
        ap_y = py - ay

        # Producto punto AB·AP
        ab_ap = ab_x * ap_x + ab_y * ap_y

        # Longitud al cuadrado de AB
        ab_len_sq = ab_x * ab_x + ab_y * ab_y

        # Evitar división por cero (A y B son el mismo punto)
        if ab_len_sq == 0:
            return DistanceCalculator.haversine_distance(point, segment_start)

        # Parámetro t de proyección (0 <= t <= 1 si está dentro del segmento)
        t = max(0, min(1, ab_ap / ab_len_sq))

        # Punto proyectado en el segmento
        proj_x = ax + t * ab_x
        proj_y = ay + t * ab_y

        proj_point = Coordinates(latitude=proj_y, longitude=proj_x)

        # Distancia del punto original al punto proyectado
        return DistanceCalculator.haversine_distance(point, proj_point)

    @staticmethod
    def is_within_radius(
        center: Coordinates,
        target: Coordinates,
        radius_km: float
    ) -> bool:
        """
        Verifica si un punto está dentro de un radio desde el centro.

        Args:
            center: Centro del círculo
            target: Punto a verificar
            radius_km: Radio en kilómetros

        Returns:
            True si está dentro del radio
        """
        distance = DistanceCalculator.haversine_distance(center, target)
        return distance <= radius_km

    @staticmethod
    def calculate_detour_for_waypoint(
        route_start: Coordinates,
        route_end: Coordinates,
        waypoint: Coordinates
    ) -> float:
        """
        Calcula el desvío adicional al insertar un waypoint en la ruta.

        Desvío = (distancia_start_waypoint + distancia_waypoint_end) - distancia_start_end

        Returns:
            Desvío en kilómetros
        """
        # Ruta original
        original_distance = DistanceCalculator.haversine_distance(route_start, route_end)

        # Ruta con waypoint
        detour_distance = (
            DistanceCalculator.haversine_distance(route_start, waypoint) +
            DistanceCalculator.haversine_distance(waypoint, route_end)
        )

        # Desvío es la diferencia
        return detour_distance - original_distance

    @staticmethod
    def find_closest_point_on_route(
        point: Coordinates,
        route_waypoints: list[Coordinates]
    ) -> Tuple[int, float]:
        """
        Encuentra el segmento más cercano de una ruta multi-waypoint.

        Args:
            point: Punto a evaluar
            route_waypoints: Lista de waypoints de la ruta

        Returns:
            Tupla (segment_index, distance) donde segment_index es el índice
            del segmento más cercano y distance es la distancia en km
        """
        if len(route_waypoints) < 2:
            return (0, float('inf'))

        min_distance = float('inf')
        closest_segment = 0

        for i in range(len(route_waypoints) - 1):
            segment_start = route_waypoints[i]
            segment_end = route_waypoints[i + 1]

            distance = DistanceCalculator.point_to_segment_distance(
                point, segment_start, segment_end
            )

            if distance < min_distance:
                min_distance = distance
                closest_segment = i

        return (closest_segment, min_distance)
```

---

## Paso 2: Servicio de Matching Geográfico Mejorado

**Archivo**: `apps/matching/infrastructure/services/geometric_matching_service.py`

```python
from typing import Optional
from apps.maps.domain.models import Coordinates
from apps.matching.infrastructure.services.distance_calculator import DistanceCalculator
from apps.trips.domain.models import Trip

class GeometricMatchingService:
    """
    Servicio especializado en matching geográfico avanzado.
    Mejora sobre el matching básico de RF-006.
    """

    def __init__(self):
        self.calculator = DistanceCalculator()

    def is_pickup_compatible(
        self,
        pickup_location: Coordinates,
        trip: Trip,
        max_deviation_km: float = 10.0
    ) -> bool:
        """
        Verifica si el punto de recogida es compatible con la ruta del trayecto.

        Usa distancia perpendicular al segmento de ruta.

        Args:
            pickup_location: Ubicación de recogida del pasajero
            trip: Trayecto a evaluar
            max_deviation_km: Desviación máxima permitida (default: 10 km)

        Returns:
            True si el pickup está cerca de la ruta
        """
        # Validar que el trip tenga coordenadas
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return False

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        # Calcular distancia perpendicular al segmento
        distance = self.calculator.point_to_segment_distance(
            pickup_location,
            trip_origin,
            trip_dest
        )

        return distance <= max_deviation_km

    def is_dropoff_compatible(
        self,
        dropoff_location: Coordinates,
        trip: Trip,
        max_deviation_km: float = 10.0
    ) -> bool:
        """
        Verifica si el punto de bajada es compatible con la ruta.
        Mismo algoritmo que pickup pero para destino.
        """
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return False

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        distance = self.calculator.point_to_segment_distance(
            dropoff_location,
            trip_origin,
            trip_dest
        )

        return distance <= max_deviation_km

    def calculate_route_compatibility_score(
        self,
        pickup: Coordinates,
        dropoff: Coordinates,
        trip: Trip
    ) -> float:
        """
        Calcula un score de compatibilidad geográfica (0-100).

        Factores:
        - Distancia pickup a ruta
        - Distancia dropoff a ruta
        - Desvío estimado

        Returns:
            Score 0-100 (mayor es mejor)
        """
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return 0.0

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        # Distancia pickup a ruta
        pickup_distance = self.calculator.point_to_segment_distance(
            pickup, trip_origin, trip_dest
        )

        # Distancia dropoff a ruta
        dropoff_distance = self.calculator.point_to_segment_distance(
            dropoff, trip_origin, trip_dest
        )

        # Score basado en cercanía (menor distancia = mayor score)
        total_distance = pickup_distance + dropoff_distance

        if total_distance <= 2:
            return 100.0
        elif total_distance <= 5:
            return 95.0
        elif total_distance <= 10:
            return 85.0
        elif total_distance <= 15:
            return 70.0
        elif total_distance <= 20:
            return 50.0
        elif total_distance <= 30:
            return 30.0
        else:
            return max(0, 30 - (total_distance - 30) * 2)

    def search_trips_by_location(
        self,
        location: Coordinates,
        radius_km: float,
        trips: list[Trip]
    ) -> list[Trip]:
        """
        Busca trayectos que pasen cerca de una ubicación.

        Args:
            location: Ubicación de referencia
            radius_km: Radio de búsqueda
            trips: Lista de trayectos a filtrar

        Returns:
            Trayectos que tienen origen o destino dentro del radio
        """
        compatible_trips = []

        for trip in trips:
            if not (trip.origin_lat and trip.origin_lng and
                    trip.destination_lat and trip.destination_lng):
                continue

            trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
            trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

            # Verificar si origen o destino están dentro del radio
            origin_in_range = self.calculator.is_within_radius(
                location, trip_origin, radius_km
            )
            dest_in_range = self.calculator.is_within_radius(
                location, trip_dest, radius_km
            )

            # O si la ruta pasa cerca de la ubicación
            distance_to_route = self.calculator.point_to_segment_distance(
                location, trip_origin, trip_dest
            )
            route_passes_nearby = distance_to_route <= radius_km

            if origin_in_range or dest_in_range or route_passes_nearby:
                compatible_trips.append(trip)

        return compatible_trips
```

---

## Paso 3: Integrar con MatchingService Existente

**Archivo**: `apps/matching/infrastructure/services/matching_service.py`

Actualizar la clase `MatchingService` para usar el nuevo servicio geométrico:

```python
from apps.matching.infrastructure.services.geometric_matching_service import GeometricMatchingService

class MatchingService(IMatchingService):
    def __init__(
        self,
        trip_repo: ITripRepository,
        booking_repo: IBookingRepository,
        travel_request_repo: ITravelRequestRepository
    ):
        self.trip_repo = trip_repo
        self.booking_repo = booking_repo
        self.travel_request_repo = travel_request_repo
        self.calculator = DetourCalculator()
        self.geometric_service = GeometricMatchingService()  # NUEVO

    async def _evaluate_trip(self, travel_request: TravelRequest, trip) -> Optional[MatchResult]:
        """Evalúa un trayecto usando matching geométrico mejorado"""

        # ... validaciones de tiempo existentes ...

        request_origin = Coordinates(
            latitude=travel_request.origin_lat,
            longitude=travel_request.origin_lng
        )
        request_dest = Coordinates(
            latitude=travel_request.destination_lat,
            longitude=travel_request.destination_lng
        )

        # MEJORA: Usar matching geométrico avanzado
        pickup_compatible = self.geometric_service.is_pickup_compatible(
            request_origin, trip, max_deviation_km=15.0
        )

        if not pickup_compatible:
            return MatchResult(
                trip_id=trip.id,
                is_compatible=False,
                reason="Origen demasiado lejos de la ruta (cálculo geométrico)",
                # ... resto de campos ...
            )

        dropoff_compatible = self.geometric_service.is_dropoff_compatible(
            request_dest, trip, max_deviation_km=15.0
        )

        if not dropoff_compatible:
            return MatchResult(
                trip_id=trip.id,
                is_compatible=False,
                reason="Destino demasiado lejos de la ruta (cálculo geométrico)",
                # ... resto de campos ...
            )

        # MEJORA: Score de compatibilidad geográfica más preciso
        geographic_score = self.geometric_service.calculate_route_compatibility_score(
            request_origin, request_dest, trip
        )

        # ... resto del cálculo de desvío y score final ...

        # Score final usando geographic_score mejorado
        final_score = (geographic_score * 0.6 + time_score * 0.4)

        # ... resto del código ...
```

---

## Paso 4: Endpoint de Búsqueda por Ubicación

**Archivo**: `apps/matching/api/versioning/v1/views.py`

Agregar nuevo endpoint:

```python
@router.get("/search-by-location", response_model=list[TripResponse])
async def search_trips_by_location(
    lat: float = Query(..., ge=-90, le=90, description="Latitud"),
    lng: float = Query(..., ge=-180, le=180, description="Longitud"),
    radius_km: float = Query(20.0, ge=1, le=100, description="Radio de búsqueda en km"),
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Buscar trayectos que pasen cerca de una ubicación específica.

    **Endpoint:** `GET /matching/v1/search-by-location?lat=36.5&lng=-6.2&radius_km=20`

    **Características:**
    - Búsqueda geográfica por radio
    - Encuentra trayectos cuya ruta pasa cerca de la ubicación
    - Útil para descubrimiento de rutas alternativas

    **Uso:**
    Usuario en Jerez busca viajes que pasen cerca de su ubicación
    """
    location = Coordinates(latitude=lat, longitude=lng)

    # Obtener todos los trayectos activos
    all_trips = await trip_repo.search(skip=0, limit=1000)

    # Filtrar por proximidad geográfica
    geometric_service = GeometricMatchingService()
    nearby_trips = geometric_service.search_trips_by_location(
        location, radius_km, all_trips
    )

    return [TripResponse(**t.model_dump()) for t in nearby_trips]
```

---

## Paso 5: Configuración de Umbrales por Conductor

**Archivo**: `apps/trips/domain/models.py`

Actualizar modelo `Trip`:

```python
class Trip(BaseModel):
    # ... campos existentes ...

    # NUEVO: Configuración de matching geográfico
    max_pickup_deviation_km: float = Field(
        default=10.0,
        ge=1,
        le=50,
        description="Desviación máxima permitida para punto de recogida (km)"
    )
    max_dropoff_deviation_km: float = Field(
        default=10.0,
        ge=1,
        le=50,
        description="Desviación máxima permitida para punto de bajada (km)"
    )
```

Actualizar `CreateTripRequest` schema:

```python
class CreateTripRequest(BaseModel):
    # ... campos existentes ...

    max_pickup_deviation_km: Optional[float] = Field(
        default=10.0,
        ge=1,
        le=50,
        description="Desviación máxima de recogida (km)"
    )
    max_dropoff_deviation_km: Optional[float] = Field(
        default=10.0,
        ge=1,
        le=50,
        description="Desviación máxima de bajada (km)"
    )
```

---

## Paso 6: Testing

**Archivo**: `tests/test_matching/test_geometric_matching.py`

```python
import pytest
from apps.maps.domain.models import Coordinates
from apps.matching.infrastructure.services.distance_calculator import DistanceCalculator
from apps.matching.infrastructure.services.geometric_matching_service import GeometricMatchingService

def test_point_to_segment_distance():
    """Test cálculo de distancia perpendicular"""
    calculator = DistanceCalculator()

    # Segmento horizontal
    segment_start = Coordinates(latitude=0.0, longitude=0.0)
    segment_end = Coordinates(latitude=0.0, longitude=10.0)

    # Punto perpendicular en el medio
    point = Coordinates(latitude=5.0, longitude=5.0)

    distance = calculator.point_to_segment_distance(point, segment_start, segment_end)

    # La distancia debería ser aproximadamente la distancia vertical
    assert distance > 0
    assert distance < 600  # Aproximadamente 555 km para lat=5°

def test_is_within_radius():
    """Test verificación de radio"""
    calculator = DistanceCalculator()

    center = Coordinates(latitude=36.5271, longitude=-6.2886)  # Cádiz
    nearby = Coordinates(latitude=36.6, longitude=-6.3)  # ~10 km
    far = Coordinates(latitude=37.5, longitude=-5.0)  # >100 km

    assert calculator.is_within_radius(center, nearby, 20.0) == True
    assert calculator.is_within_radius(center, far, 20.0) == False

def test_calculate_detour_for_waypoint():
    """Test cálculo de desvío con waypoint"""
    calculator = DistanceCalculator()

    # Ruta Cádiz → Sevilla
    start = Coordinates(latitude=36.5271, longitude=-6.2886)
    end = Coordinates(latitude=37.3891, longitude=-5.9845)

    # Waypoint en Jerez (está en la ruta)
    waypoint = Coordinates(latitude=36.6866, longitude=-6.1365)

    detour = calculator.calculate_detour_for_waypoint(start, end, waypoint)

    # El desvío debería ser pequeño ya que Jerez está en la ruta
    assert detour >= 0
    assert detour < 30  # Menos de 30 km de desvío

@pytest.mark.asyncio
async def test_search_trips_by_location():
    """Test búsqueda por ubicación"""
    # Crear trayectos de prueba
    trips = [
        Trip(
            origin="Cádiz",
            destination="Sevilla",
            origin_lat=36.5271,
            origin_lng=-6.2886,
            destination_lat=37.3891,
            destination_lng=-5.9845,
            # ... otros campos ...
        )
    ]

    service = GeometricMatchingService()

    # Buscar desde Jerez (debe encontrar el trayecto Cádiz-Sevilla)
    jerez = Coordinates(latitude=36.6866, longitude=-6.1365)
    results = service.search_trips_by_location(jerez, radius_km=30.0, trips=trips)

    assert len(results) > 0
    assert results[0].origin == "Cádiz"

@pytest.mark.asyncio
async def test_geometric_matching_endpoint(client):
    """Test endpoint de búsqueda geográfica"""
    response = await client.get(
        "/api/v1/matching/v1/search-by-location?lat=36.6866&lng=-6.1365&radius_km=30"
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

---

## Checklist de Implementación

- [ ] Crear `DistanceCalculator` con:
  - [ ] `point_to_segment_distance()` - Distancia perpendicular precisa
  - [ ] `is_within_radius()` - Verificación de radio
  - [ ] `calculate_detour_for_waypoint()` - Cálculo de desvío
  - [ ] `find_closest_point_on_route()` - Segmento más cercano
- [ ] Crear `GeometricMatchingService` con:
  - [ ] `is_pickup_compatible()` - Validación pickup mejorada
  - [ ] `is_dropoff_compatible()` - Validación dropoff mejorada
  - [ ] `calculate_route_compatibility_score()` - Score geográfico
  - [ ] `search_trips_by_location()` - Búsqueda por radio
- [ ] Integrar con `MatchingService` existente
- [ ] Agregar campos de configuración a `Trip`:
  - [ ] `max_pickup_deviation_km`
  - [ ] `max_dropoff_deviation_km`
- [ ] Endpoint `GET /search-by-location`
- [ ] Tests:
  - [ ] Test distancia perpendicular
  - [ ] Test radio de búsqueda
  - [ ] Test cálculo de desvío
  - [ ] Test búsqueda por ubicación
  - [ ] Test integración con matching
- [ ] Documentar en Swagger
- [ ] Verificar en /docs

---

## Verificación

```bash
# Buscar trayectos cerca de una ubicación (Jerez)
curl "http://localhost:8000/api/v1/matching/v1/search-by-location?lat=36.6866&lng=-6.1365&radius_km=30"

# Crear trayecto con umbrales personalizados
curl -X POST http://localhost:8000/api/v1/trips/v1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-15",
    "departure_time": "09:00:00",
    "available_seats": 3,
    "max_detour_minutes": 30,
    "max_pickup_deviation_km": 15.0,
    "max_dropoff_deviation_km": 15.0
  }'

# Ver mejoras en matching
curl -X POST http://localhost:8000/api/v1/matching/v1/travel-requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "origin_address": "Jerez de la Frontera, España",
    "destination_address": "Dos Hermanas, España",
    "travel_date": "2025-12-15",
    "time_from": "09:00:00"
  }'
```

---

## Criterios de Aceptación

✅ Cálculo preciso de distancia perpendicular a segmento de ruta
✅ Búsqueda de trayectos por ubicación y radio
✅ Umbrales de desviación configurables por conductor
✅ Score de compatibilidad geográfica mejorado
✅ Integración transparente con matching existente
✅ Mejora en precisión de matches sin romper funcionalidad actual

---

## Mejoras Futuras

- Implementar proyección esférica precisa (actualmente usa aproximación cartesiana)
- Soporte para rutas multi-waypoint reales (no solo origen-destino)
- Optimización de búsqueda geográfica con índices geoespaciales de MongoDB
- Visualización de área de cobertura del trayecto en mapa
- Cálculo de ruta óptima al insertar waypoints dinámicamente

---

## Próximo Paso

Una vez completado RF-BONUS-001, proceder con:
- **RF-BONUS-002**: Estimación de CO₂ Evitado
