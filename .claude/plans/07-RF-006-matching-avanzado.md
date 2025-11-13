# Plan: RF-006 - Motor de Asociación de Trayectos (Matching Avanzado)

**Issue**: #6
**Prioridad**: ALTA (Core MVP - Complejo)
**Estimación**: 6-8 horas
**Dependencias**:
- 02-RF-001-publicacion-trayectos.md (completado)
- 06-RF-005-visualizacion-mapas.md (completado - necesita geocoding)

---

## Objetivo

Implementar un sistema de matching automático que identifica coincidencias entre trayectos publicados y peticiones de viaje, considerando restricciones geográficas, temporales y de **desvío máximo acumulativo**.

---

## Análisis Previo - Conceptos Clave

### 🔑 Conceptos del Motor de Matching

**1. TravelRequest (Petición de Viaje)**
- Solicitud de un pasajero que busca un viaje
- Contiene: origen, destino, fecha, rango horario opcional
- El motor evalúa qué trayectos pueden acomodar esta petición

**2. Roadmap Dinámico**
- Lista ordenada de waypoints (puntos intermedios) del trayecto
- Ejemplo: `Cádiz → Jerez → Dos Hermanas → Sevilla`
- Se actualiza dinámicamente al aceptar nuevos pasajeros

**3. Desvío Acumulativo (CRÍTICO)**
- `max_detour_minutes`: Límite de desvío que el conductor tolera (ej: 30 min)
- `current_detour_minutes`: Desvío ya consumido por pasajeros previos
- **Regla**: `current_detour + new_detour ≤ max_detour`
- Si se excede, el trayecto NO es compatible

**4. Matching Geográfico**
- Origen de petición debe estar cerca de algún punto del trayecto
- Destino debe estar en un punto posterior del roadmap
- No se permiten inserciones que alteren el orden lógico

**5. Matching Temporal**
- Coincidencia exacta de fecha
- Opcionalmente, respeta rango horario del pasajero

### Arquitectura Objetivo
```
apps/matching/
├── domain/
│   ├── models.py              # TravelRequest, MatchResult, MatchScore
│   └── services/
│       └── matching_service.py # IMatchingService (interface)
├── infrastructure/
│   ├── dependencies.py
│   └── services/
│       ├── matching_service.py    # MatchingService (implementación)
│       └── detour_calculator.py   # Cálculo de desvíos
└── api/
    ├── urls.py
    └── versioning/v1/
        ├── views.py           # Endpoints de matching
        └── schemas/
            ├── requests.py    # TravelRequestCreate, AcceptMatchRequest
            └── responses.py   # MatchResultResponse, TravelRequestResponse
```

---

## Paso 1: Modelos de Dominio

**Archivo**: `apps/matching/domain/models.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional
from enum import Enum

class TravelRequestStatus(str, Enum):
    """Estados de una petición de viaje"""
    PENDING = "pending"
    MATCHED = "matched"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class TravelRequest(BaseModel):
    """
    Petición de viaje de un pasajero.
    El motor de matching evalúa qué trayectos pueden acomodar esta petición.
    """
    # Identificador
    id: Optional[str] = None

    # Pasajero
    passenger_id: str

    # Ubicaciones (coordenadas)
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)

    # Direcciones textuales (opcional)
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None

    # Criterios temporales
    travel_date: date
    time_from: Optional[time] = None  # "A partir de esta hora"
    time_to: Optional[time] = None    # "Antes de esta hora"

    # Detalles
    seats_requested: int = Field(default=1, ge=1, le=10)
    passenger_notes: Optional[str] = Field(None, max_length=500)

    # Estado
    status: TravelRequestStatus = Field(default=TravelRequestStatus.PENDING)
    matched_trip_id: Optional[str] = None

    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "passenger_id": "507f1f77bcf86cd799439011",
                "origin_lat": 36.5271,
                "origin_lng": -6.2886,
                "destination_lat": 37.3891,
                "destination_lng": -5.9845,
                "origin_address": "Jerez de la Frontera",
                "destination_address": "Dos Hermanas",
                "travel_date": "2025-12-15",
                "time_from": "09:00:00",
                "seats_requested": 1
            }
        }

class WaypointInsertion(BaseModel):
    """Representa la inserción de waypoints en el roadmap"""
    pickup_index: int = Field(..., description="Índice donde insertar pickup")
    dropoff_index: int = Field(..., description="Índice donde insertar dropoff")
    pickup_location: dict = Field(..., description="Coordenadas de recogida")
    dropoff_location: dict = Field(..., description="Coordenadas de bajada")
    additional_detour_minutes: int = Field(..., description="Desvío adicional estimado")

class MatchScore(BaseModel):
    """Puntuación de compatibilidad de un match"""
    trip_id: str
    score: float = Field(..., ge=0, le=100, description="Puntuación 0-100")
    detour_additional: int = Field(..., description="Desvío adicional en minutos")
    proximity_score: float = Field(..., description="Proximidad geográfica")
    time_compatibility_score: float = Field(..., description="Compatibilidad temporal")

class MatchResult(BaseModel):
    """
    Resultado de evaluación de matching.
    Indica si un trayecto puede acomodar la petición.
    """
    trip_id: str
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
    driver_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "trip_id": "507f1f77bcf86cd799439012",
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
                    "trip_id": "507f1f77bcf86cd799439012",
                    "score": 85.5,
                    "detour_additional": 20,
                    "proximity_score": 90.0,
                    "time_compatibility_score": 95.0
                }
            }
        }
```

---

## Paso 2: Repositorio de TravelRequest

**Archivo**: `apps/matching/domain/repositories/travel_request_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from datetime import date
from apps.matching.domain.models import TravelRequest

class ITravelRequestRepository(ABC):
    """Contrato para el repositorio de peticiones de viaje"""

    @abstractmethod
    async def create(self, travel_request: TravelRequest) -> TravelRequest:
        """Crea una nueva petición de viaje"""
        pass

    @abstractmethod
    async def get_by_id(self, request_id: str) -> Optional[TravelRequest]:
        """Obtiene petición por ID"""
        pass

    @abstractmethod
    async def get_by_passenger(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[TravelRequest]:
        """Obtiene peticiones de un pasajero"""
        pass

    @abstractmethod
    async def get_pending_by_date(self, travel_date: date) -> list[TravelRequest]:
        """Obtiene peticiones pendientes para una fecha específica"""
        pass

    @abstractmethod
    async def update(self, request_id: str, travel_request: TravelRequest) -> bool:
        """Actualiza petición"""
        pass

    @abstractmethod
    async def delete(self, request_id: str) -> bool:
        """Elimina petición"""
        pass
```

**Archivo**: `apps/matching/infrastructure/repositories/travel_request_repository.py`

```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, date
from typing import Optional
from bson import ObjectId

from apps.matching.domain.models import TravelRequest
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository

class TravelRequestRepository(ITravelRequestRepository):
    """Implementación MongoDB del repositorio de peticiones de viaje"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db["travel_requests"]

    async def create(self, travel_request: TravelRequest) -> TravelRequest:
        """Crea petición en MongoDB"""
        request_dict = travel_request.model_dump(exclude={"id"}, mode="json")
        result = await self._collection.insert_one(request_dict)
        travel_request.id = str(result.inserted_id)
        return travel_request

    async def get_by_id(self, request_id: str) -> Optional[TravelRequest]:
        """Obtiene por ID"""
        try:
            doc = await self._collection.find_one({"_id": ObjectId(request_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return TravelRequest(**doc)
            return None
        except Exception:
            return None

    async def get_by_passenger(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[TravelRequest]:
        """Obtiene peticiones de un pasajero"""
        cursor = self._collection.find({
            "passenger_id": passenger_id
        }).sort("created_at", -1).skip(skip).limit(limit)

        requests = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            requests.append(TravelRequest(**doc))
        return requests

    async def get_pending_by_date(self, travel_date: date) -> list[TravelRequest]:
        """Obtiene peticiones pendientes para una fecha"""
        cursor = self._collection.find({
            "travel_date": travel_date.isoformat(),
            "status": "pending"
        })

        requests = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            requests.append(TravelRequest(**doc))
        return requests

    async def update(self, request_id: str, travel_request: TravelRequest) -> bool:
        """Actualiza petición"""
        travel_request.updated_at = datetime.utcnow()
        update_dict = travel_request.model_dump(exclude={"id", "created_at"}, mode="json")

        result = await self._collection.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0

    async def delete(self, request_id: str) -> bool:
        """Elimina petición"""
        result = await self._collection.delete_one({"_id": ObjectId(request_id)})
        return result.deleted_count > 0
```

---

## Paso 3: Servicio de Cálculo de Desvíos

**Archivo**: `apps/matching/infrastructure/services/detour_calculator.py`

```python
import math
from apps.maps.domain.models import Coordinates

class DetourCalculator:
    """Utilidad para calcular desvíos geográficos"""

    @staticmethod
    def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        """
        Calcula distancia en km entre dos coordenadas usando fórmula de Haversine.

        Returns:
            Distancia en kilómetros
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
    def estimate_detour_minutes(distance_km: float, avg_speed_kmh: float = 80) -> int:
        """
        Estima tiempo de desvío en minutos.

        Args:
            distance_km: Distancia del desvío en km
            avg_speed_kmh: Velocidad promedio (default: 80 km/h)

        Returns:
            Tiempo estimado en minutos
        """
        hours = distance_km / avg_speed_kmh
        return int(hours * 60)

    @staticmethod
    def is_point_near_segment(
        point: Coordinates,
        segment_start: Coordinates,
        segment_end: Coordinates,
        threshold_km: float = 10.0
    ) -> bool:
        """
        Verifica si un punto está cerca de un segmento de ruta.

        Args:
            point: Punto a verificar
            segment_start: Inicio del segmento
            segment_end: Fin del segmento
            threshold_km: Distancia máxima en km (default: 10 km)

        Returns:
            True si el punto está cerca del segmento
        """
        # Calcular distancia del punto a ambos extremos
        dist_to_start = DetourCalculator.haversine_distance(point, segment_start)
        dist_to_end = DetourCalculator.haversine_distance(point, segment_end)

        # Si está cerca de alguno de los extremos, es compatible
        if dist_to_start <= threshold_km or dist_to_end <= threshold_km:
            return True

        # Verificar distancia perpendicular al segmento (simplificado)
        # Para MVP, usar promedio de distancias como aproximación
        avg_distance = (dist_to_start + dist_to_end) / 2
        return avg_distance <= threshold_km
```

---

## Paso 4: Interface del Servicio de Matching

**Archivo**: `apps/matching/domain/services/matching_service.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.matching.domain.models import TravelRequest, MatchResult

class IMatchingService(ABC):
    """Contrato para el servicio de matching"""

    @abstractmethod
    async def find_compatible_trips(
        self,
        travel_request: TravelRequest
    ) -> list[MatchResult]:
        """
        Encuentra trayectos compatibles para una petición de viaje.

        Returns:
            Lista de MatchResult ordenados por score (mejor primero)
        """
        pass

    @abstractmethod
    async def evaluate_compatibility(
        self,
        travel_request: TravelRequest,
        trip_id: str
    ) -> Optional[MatchResult]:
        """
        Evalúa si un trayecto específico es compatible.

        Returns:
            MatchResult con análisis detallado
        """
        pass

    @abstractmethod
    async def accept_match(
        self,
        travel_request_id: str,
        trip_id: str,
        passenger_id: str
    ) -> bool:
        """
        Acepta un match: crea booking y actualiza trip roadmap.

        Returns:
            True si se aceptó exitosamente
        """
        pass
```

---

## Paso 5: Implementación del Servicio de Matching

**Archivo**: `apps/matching/infrastructure/services/matching_service.py`

```python
from typing import Optional
from datetime import time as time_type
from fastapi import HTTPException, status

from apps.matching.domain.models import (
    TravelRequest, MatchResult, MatchScore, WaypointInsertion
)
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.infrastructure.services.detour_calculator import DetourCalculator
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.maps.domain.models import Coordinates

class MatchingService(IMatchingService):
    """Implementación del motor de matching"""

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

    async def find_compatible_trips(
        self,
        travel_request: TravelRequest
    ) -> list[MatchResult]:
        """
        Algoritmo principal de matching.

        Pasos:
        1. Filtrar trips por fecha exacta
        2. Para cada trip, evaluar compatibilidad:
           - Geográfica (origen/destino cerca del trayecto)
           - Temporal (rango horario)
           - Desvío (current + additional ≤ max)
        3. Calcular score de compatibilidad
        4. Ordenar por score descendente
        """
        # Paso 1: Obtener trayectos de la fecha solicitada
        trips = await self.trip_repo.search(
            date_from=travel_request.travel_date,
            skip=0,
            limit=1000  # TODO: Optimizar con índices
        )

        # Filtrar solo activos con plazas
        trips = [
            t for t in trips
            if t.status == "active" and t.available_seats >= travel_request.seats_requested
        ]

        # Paso 2: Evaluar cada trayecto
        results = []
        for trip in trips:
            result = await self._evaluate_trip(travel_request, trip)
            if result:
                results.append(result)

        # Paso 3: Ordenar por score (mejor primero)
        compatible_results = [r for r in results if r.is_compatible]
        compatible_results.sort(
            key=lambda r: r.match_score.score if r.match_score else 0,
            reverse=True
        )

        return compatible_results

    async def _evaluate_trip(self, travel_request: TravelRequest, trip) -> Optional[MatchResult]:
        """Evalúa un trayecto específico contra la petición"""

        # Verificar compatibilidad temporal
        if travel_request.time_from or travel_request.time_to:
            if not self._is_time_compatible(
                trip.departure_time,
                travel_request.time_from,
                travel_request.time_to
            ):
                return MatchResult(
                    trip_id=trip.id,
                    is_compatible=False,
                    reason="Horario no compatible",
                    trip_origin=trip.origin,
                    trip_destination=trip.destination,
                    departure_time=trip.departure_time,
                    available_seats=trip.available_seats,
                    current_detour_minutes=trip.current_detour_minutes,
                    max_detour_minutes=trip.max_detour_minutes,
                    driver_id=trip.driver_id
                )

        # Crear coordenadas
        request_origin = Coordinates(
            latitude=travel_request.origin_lat,
            longitude=travel_request.origin_lng
        )
        request_dest = Coordinates(
            latitude=travel_request.destination_lat,
            longitude=travel_request.destination_lng
        )

        # Si el trip no tiene coordenadas, no se puede evaluar
        if not (trip.origin_lat and trip.origin_lng and
                trip.destination_lat and trip.destination_lng):
            return MatchResult(
                trip_id=trip.id,
                is_compatible=False,
                reason="Trayecto sin coordenadas geocodificadas",
                trip_origin=trip.origin,
                trip_destination=trip.destination,
                departure_time=trip.departure_time,
                available_seats=trip.available_seats,
                current_detour_minutes=trip.current_detour_minutes,
                max_detour_minutes=trip.max_detour_minutes,
                driver_id=trip.driver_id
            )

        trip_origin = Coordinates(latitude=trip.origin_lat, longitude=trip.origin_lng)
        trip_dest = Coordinates(latitude=trip.destination_lat, longitude=trip.destination_lng)

        # Verificar compatibilidad geográfica
        # Origen de request debe estar cerca del segmento del trip
        if not self.calculator.is_point_near_segment(
            request_origin, trip_origin, trip_dest, threshold_km=15.0
        ):
            return MatchResult(
                trip_id=trip.id,
                is_compatible=False,
                reason="Origen demasiado lejos de la ruta",
                trip_origin=trip.origin,
                trip_destination=trip.destination,
                departure_time=trip.departure_time,
                available_seats=trip.available_seats,
                current_detour_minutes=trip.current_detour_minutes,
                max_detour_minutes=trip.max_detour_minutes,
                driver_id=trip.driver_id
            )

        # Destino de request debe estar cerca del segmento
        if not self.calculator.is_point_near_segment(
            request_dest, trip_origin, trip_dest, threshold_km=15.0
        ):
            return MatchResult(
                trip_id=trip.id,
                is_compatible=False,
                reason="Destino demasiado lejos de la ruta",
                trip_origin=trip.origin,
                trip_destination=trip.destination,
                departure_time=trip.departure_time,
                available_seats=trip.available_seats,
                current_detour_minutes=trip.current_detour_minutes,
                max_detour_minutes=trip.max_detour_minutes,
                driver_id=trip.driver_id
            )

        # Calcular desvío adicional estimado
        # Simplificación: distancia del desvío = distancia origen request + distancia destino request
        detour_dist_pickup = self.calculator.haversine_distance(trip_origin, request_origin)
        detour_dist_dropoff = self.calculator.haversine_distance(request_dest, trip_dest)
        total_detour_km = detour_dist_pickup + detour_dist_dropoff

        additional_detour_minutes = self.calculator.estimate_detour_minutes(total_detour_km)

        # REGLA CRÍTICA: Verificar desvío máximo acumulativo
        projected_total = trip.current_detour_minutes + additional_detour_minutes

        if projected_total > trip.max_detour_minutes:
            return MatchResult(
                trip_id=trip.id,
                is_compatible=False,
                reason=f"Desvío excedido: {projected_total} > {trip.max_detour_minutes} min",
                trip_origin=trip.origin,
                trip_destination=trip.destination,
                departure_time=trip.departure_time,
                available_seats=trip.available_seats,
                current_detour_minutes=trip.current_detour_minutes,
                max_detour_minutes=trip.max_detour_minutes,
                additional_detour_minutes=additional_detour_minutes,
                projected_total_detour=projected_total,
                driver_id=trip.driver_id
            )

        # Calcular score de compatibilidad
        proximity_score = self._calculate_proximity_score(
            detour_dist_pickup, detour_dist_dropoff
        )
        time_score = self._calculate_time_score(
            trip.departure_time,
            travel_request.time_from,
            travel_request.time_to
        )

        # Score final (0-100)
        final_score = (proximity_score * 0.6 + time_score * 0.4)

        # Propuesta de inserción (simplificada para MVP)
        proposed_insertion = WaypointInsertion(
            pickup_index=0,
            dropoff_index=1,
            pickup_location={
                "lat": request_origin.latitude,
                "lng": request_origin.longitude,
                "address": travel_request.origin_address
            },
            dropoff_location={
                "lat": request_dest.latitude,
                "lng": request_dest.longitude,
                "address": travel_request.destination_address
            },
            additional_detour_minutes=additional_detour_minutes
        )

        match_score = MatchScore(
            trip_id=trip.id,
            score=final_score,
            detour_additional=additional_detour_minutes,
            proximity_score=proximity_score,
            time_compatibility_score=time_score
        )

        return MatchResult(
            trip_id=trip.id,
            is_compatible=True,
            trip_origin=trip.origin,
            trip_destination=trip.destination,
            departure_time=trip.departure_time,
            available_seats=trip.available_seats,
            current_detour_minutes=trip.current_detour_minutes,
            max_detour_minutes=trip.max_detour_minutes,
            additional_detour_minutes=additional_detour_minutes,
            projected_total_detour=projected_total,
            proposed_insertion=proposed_insertion,
            match_score=match_score,
            driver_id=trip.driver_id
        )

    def _is_time_compatible(
        self,
        trip_time: time_type,
        time_from: Optional[time_type],
        time_to: Optional[time_type]
    ) -> bool:
        """Verifica compatibilidad de horario"""
        if time_from and trip_time < time_from:
            return False
        if time_to and trip_time > time_to:
            return False
        return True

    def _calculate_proximity_score(
        self,
        pickup_dist_km: float,
        dropoff_dist_km: float
    ) -> float:
        """Calcula score de proximidad (0-100)"""
        # Menor distancia = mayor score
        total_dist = pickup_dist_km + dropoff_dist_km

        if total_dist <= 5:
            return 100.0
        elif total_dist <= 10:
            return 90.0
        elif total_dist <= 20:
            return 70.0
        elif total_dist <= 30:
            return 50.0
        else:
            return max(0, 50 - (total_dist - 30))

    def _calculate_time_score(
        self,
        trip_time: time_type,
        time_from: Optional[time_type],
        time_to: Optional[time_type]
    ) -> float:
        """Calcula score de compatibilidad temporal (0-100)"""
        if not time_from and not time_to:
            return 100.0  # Sin restricción = perfecto

        # Si está en el rango, score alto
        if time_from and time_to:
            if time_from <= trip_time <= time_to:
                return 100.0
            else:
                return 50.0  # Fuera de rango

        if time_from:
            if trip_time >= time_from:
                return 100.0
            else:
                return 50.0

        if time_to:
            if trip_time <= time_to:
                return 100.0
            else:
                return 50.0

        return 100.0

    async def evaluate_compatibility(
        self,
        travel_request: TravelRequest,
        trip_id: str
    ) -> Optional[MatchResult]:
        """Evalúa un trayecto específico"""
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            return None

        return await self._evaluate_trip(travel_request, trip)

    async def accept_match(
        self,
        travel_request_id: str,
        trip_id: str,
        passenger_id: str
    ) -> bool:
        """
        Acepta un match:
        1. Crea Booking
        2. Actualiza roadmap del Trip
        3. Actualiza current_detour_minutes
        4. Actualiza TravelRequest status
        """
        # Obtener travel request
        travel_request = await self.travel_request_repo.get_by_id(travel_request_id)
        if not travel_request:
            raise HTTPException(status_code=404, detail="Petición no encontrada")

        # Validar que es del pasajero correcto
        if travel_request.passenger_id != passenger_id:
            raise HTTPException(status_code=403, detail="No autorizado")

        # Re-evaluar compatibilidad
        match_result = await self.evaluate_compatibility(travel_request, trip_id)
        if not match_result or not match_result.is_compatible:
            raise HTTPException(
                status_code=400,
                detail="El trayecto ya no es compatible"
            )

        # Crear booking usando el servicio de booking (RF-003)
        from apps.trips.infrastructure.services.booking_service import BookingService

        booking_service = BookingService(
            self.booking_repo,
            self.trip_repo
        )

        await booking_service.create_booking(
            trip_id=trip_id,
            passenger_id=passenger_id,
            seats_requested=travel_request.seats_requested,
            passenger_notes=travel_request.passenger_notes
        )

        # Actualizar trip: roadmap y current_detour
        trip = await self.trip_repo.get_by_id(trip_id)
        if trip:
            # Actualizar roadmap (simplificado para MVP)
            if match_result.proposed_insertion:
                new_waypoint = {
                    "type": "pickup",
                    "passenger_id": passenger_id,
                    "location": match_result.proposed_insertion.pickup_location
                }
                trip.roadmap.append(new_waypoint)

                new_waypoint = {
                    "type": "dropoff",
                    "passenger_id": passenger_id,
                    "location": match_result.proposed_insertion.dropoff_location
                }
                trip.roadmap.append(new_waypoint)

            # Actualizar desvío acumulado
            trip.current_detour_minutes += match_result.additional_detour_minutes
            await self.trip_repo.update(trip_id, trip)

        # Actualizar travel request
        travel_request.status = "accepted"
        travel_request.matched_trip_id = trip_id
        await self.travel_request_repo.update(travel_request_id, travel_request)

        return True
```

---

## Paso 6: Dependency Injection

**Archivo**: `apps/matching/infrastructure/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.database import get_database
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.infrastructure.repositories.travel_request_repository import TravelRequestRepository
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.infrastructure.services.matching_service import MatchingService
from apps.trips.infrastructure.dependencies import get_trip_repository, get_booking_repository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository

async def get_travel_request_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> ITravelRequestRepository:
    """Inyecta repositorio de travel requests"""
    return TravelRequestRepository(db)

async def get_matching_service(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
) -> IMatchingService:
    """Inyecta servicio de matching"""
    return MatchingService(trip_repo, booking_repo, travel_request_repo)
```

---

## Paso 7: DTOs (Schemas)

**Archivo**: `apps/matching/api/versioning/v1/schemas/requests.py`

```python
from pydantic import BaseModel, Field
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

    class Config:
        json_schema_extra = {
            "example": {
                "origin_address": "Jerez de la Frontera, España",
                "destination_address": "Dos Hermanas, España",
                "travel_date": "2025-12-15",
                "time_from": "09:00:00",
                "time_to": "11:00:00",
                "seats_requested": 1
            }
        }

class AcceptMatchRequest(BaseModel):
    """Request para aceptar un match"""
    trip_id: str = Field(..., description="ID del trayecto a reservar")
```

**Archivo**: `apps/matching/api/versioning/v1/schemas/responses.py`

```python
from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional
from apps.matching.domain.models import (
    TravelRequest, MatchResult, MatchScore, WaypointInsertion
)

# Reutilizar modelos del dominio
class TravelRequestResponse(TravelRequest):
    """Response de travel request"""
    pass

class MatchResultResponse(MatchResult):
    """Response de resultado de matching"""
    pass

class MatchListResponse(BaseModel):
    """Lista de matches sugeridos"""
    travel_request_id: str
    matches: list[MatchResultResponse]
    total_matches: int
```

---

## Paso 8: Endpoints

**Archivo**: `apps/matching/api/versioning/v1/views.py`

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.matching.domain.models import TravelRequest
from apps.matching.domain.services.matching_service import IMatchingService
from apps.matching.domain.repositories.travel_request_repository import ITravelRequestRepository
from apps.matching.infrastructure.dependencies import (
    get_matching_service,
    get_travel_request_repository
)
from apps.matching.api.versioning.v1.schemas.requests import (
    CreateTravelRequestRequest,
    AcceptMatchRequest
)
from apps.matching.api.versioning.v1.schemas.responses import (
    TravelRequestResponse,
    MatchListResponse,
    MatchResultResponse
)
from apps.users.infrastructure.dependencies import get_current_user
from apps.users.domain.models import User
from apps.maps.domain.services.map_service import IMapService
from apps.maps.infrastructure.dependencies import get_map_service

router = APIRouter()

@router.post("/travel-requests", response_model=TravelRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_travel_request(
    payload: CreateTravelRequestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)],
    map_service: Annotated[IMapService, Depends(get_map_service)]
):
    """
    Crear petición de viaje.

    **Proceso:**
    1. Usuario especifica origen, destino, fecha
    2. Sistema geocodifica las ubicaciones
    3. Crea TravelRequest
    4. Listo para ejecutar matching
    """
    # Geocodificar origen
    origin_coords = await map_service.geocode(payload.origin_address)
    if not origin_coords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró origen: {payload.origin_address}"
        )

    # Geocodificar destino
    dest_coords = await map_service.geocode(payload.destination_address)
    if not dest_coords:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró destino: {payload.destination_address}"
        )

    # Crear travel request
    travel_request = TravelRequest(
        passenger_id=current_user.id,
        origin_lat=origin_coords.latitude,
        origin_lng=origin_coords.longitude,
        destination_lat=dest_coords.latitude,
        destination_lng=dest_coords.longitude,
        origin_address=payload.origin_address,
        destination_address=payload.destination_address,
        travel_date=payload.travel_date,
        time_from=payload.time_from,
        time_to=payload.time_to,
        seats_requested=payload.seats_requested,
        passenger_notes=payload.passenger_notes
    )

    created = await travel_request_repo.create(travel_request)

    return TravelRequestResponse(**created.model_dump())

@router.get("/travel-requests/{request_id}/matches", response_model=MatchListResponse)
async def find_matches(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    matching_service: Annotated[IMatchingService, Depends(get_matching_service)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)]
):
    """
    Encontrar trayectos compatibles para una petición.

    **Motor de Matching:**
    - Evalúa coincidencia geográfica
    - Evalúa coincidencia temporal
    - Verifica desvío máximo acumulativo
    - Calcula score de compatibilidad
    - Ordena por mejor match

    **Retorna:**
    Lista de trayectos sugeridos ordenados por score
    """
    # Obtener travel request
    travel_request = await travel_request_repo.get_by_id(request_id)
    if not travel_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Petición de viaje no encontrada"
        )

    # Validar que es del usuario actual
    if travel_request.passenger_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )

    # Ejecutar matching
    matches = await matching_service.find_compatible_trips(travel_request)

    return MatchListResponse(
        travel_request_id=request_id,
        matches=[MatchResultResponse(**m.model_dump()) for m in matches],
        total_matches=len(matches)
    )

@router.post("/travel-requests/{request_id}/accept", status_code=status.HTTP_201_CREATED)
async def accept_match(
    request_id: str,
    payload: AcceptMatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    matching_service: Annotated[IMatchingService, Depends(get_matching_service)]
):
    """
    Aceptar un match y crear reserva.

    **Proceso:**
    1. Re-valida compatibilidad
    2. Crea Booking
    3. Actualiza roadmap del Trip
    4. Actualiza current_detour_minutes
    5. Marca TravelRequest como 'accepted'
    """
    success = await matching_service.accept_match(
        travel_request_id=request_id,
        trip_id=payload.trip_id,
        passenger_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo aceptar el match"
        )

    return {"message": "Match aceptado exitosamente", "trip_id": payload.trip_id}

@router.get("/my-travel-requests", response_model=list[TravelRequestResponse])
async def get_my_travel_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    travel_request_repo: Annotated[ITravelRequestRepository, Depends(get_travel_request_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Listar mis peticiones de viaje"""
    requests = await travel_request_repo.get_by_passenger(
        current_user.id,
        skip=skip,
        limit=limit
    )

    return [TravelRequestResponse(**r.model_dump()) for r in requests]
```

---

## Paso 9: Registrar Router

**Archivo**: `apps/matching/api/urls.py`

```python
from fastapi import APIRouter
from apps.matching.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1", tags=["Matching"])
```

**Actualizar**: `main.py`

```python
from apps.matching.api.urls import router as matching_router

app.include_router(matching_router, prefix="/api/v1/matching", tags=["Matching"])
```

---

## Paso 10: Crear Índices

**Archivo**: `scripts/create_indexes.py`

```python
async def create_matching_indexes():
    """Índices para matching"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Índice para buscar por fecha
    await db.travel_requests.create_index([("travel_date", 1)])

    # Índice para buscar por pasajero
    await db.travel_requests.create_index([("passenger_id", 1)])

    # Índice para buscar pendientes
    await db.travel_requests.create_index([("status", 1)])

    # Índice geoespacial para matching
    await db.travel_requests.create_index([("origin_lat", 1), ("origin_lng", 1)])

    print("✅ Índices de matching creados")
    client.close()
```

---

## Checklist de Implementación

- [ ] Modelo TravelRequest en domain/models.py
- [ ] Modelos MatchResult, MatchScore, WaypointInsertion
- [ ] Interface ITravelRequestRepository
- [ ] Implementación TravelRequestRepository (MongoDB)
- [ ] DetourCalculator (haversine, estimaciones)
- [ ] Interface IMatchingService
- [ ] Implementación MatchingService:
  - [ ] find_compatible_trips() - Algoritmo principal
  - [ ] _evaluate_trip() - Evaluación individual
  - [ ] Validación geográfica
  - [ ] Validación temporal
  - [ ] Validación de desvío acumulativo
  - [ ] Cálculo de scores
  - [ ] accept_match() - Aceptar y crear booking
- [ ] Dependency injection
- [ ] Schemas de request/response
- [ ] Endpoints:
  - [ ] POST /travel-requests (crear petición)
  - [ ] GET /travel-requests/{id}/matches (encontrar matches)
  - [ ] POST /travel-requests/{id}/accept (aceptar match)
  - [ ] GET /my-travel-requests (listar mis peticiones)
- [ ] Router registrado
- [ ] Crear índices
- [ ] Tests
- [ ] Verificar en /docs

---

## Verificación

```bash
# Crear petición de viaje
curl -X POST http://localhost:8000/api/v1/matching/v1/travel-requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "origin_address": "Jerez de la Frontera, España",
    "destination_address": "Dos Hermanas, España",
    "travel_date": "2025-12-15",
    "time_from": "09:00:00",
    "seats_requested": 1
  }'

# Encontrar matches
curl http://localhost:8000/api/v1/matching/v1/travel-requests/<REQUEST_ID>/matches \
  -H "Authorization: Bearer <TOKEN>"

# Aceptar match
curl -X POST http://localhost:8000/api/v1/matching/v1/travel-requests/<REQUEST_ID>/accept \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"trip_id": "<TRIP_ID>"}'

# Ver mis peticiones
curl http://localhost:8000/api/v1/matching/v1/my-travel-requests \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Criterios de Aceptación (de Issue #6)

✅ Sistema ejecuta algoritmo de matching automatizado
✅ Identifica coincidencias geográficas y temporales
✅ Verifica desvío máximo acumulativo
✅ Genera sugerencias priorizadas
✅ Usuarios reciben matches relevantes
✅ Algoritmo funciona con búsqueda exacta y aproximada
✅ Matching se actualiza al publicar nuevos trayectos

---

## Próximo Paso

Una vez completado RF-006, proceder con:
- **RF-BONUS-001**: Matching Aproximado Geográfico (mejora del actual)
- **RF-BONUS-002**: Estimación de CO₂ Evitado
- **RF-BONUS-003**: Visualización de Reservas de Otros
- **RF-BONUS-004**: Chat Simulado
