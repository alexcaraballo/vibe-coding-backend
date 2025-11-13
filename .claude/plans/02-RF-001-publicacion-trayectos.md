# Plan: RF-001 - Publicación de Trayectos

**Issue**: #1
**Prioridad**: ALTA (Core MVP)
**Estimación**: 3-4 horas
**Dependencias**: 01-RF-INF-001-gestion-usuarios.md (completado)

---

## Objetivo

Permitir a los conductores publicar trayectos disponibles para compartir, creando registros en el sistema con toda la información necesaria del viaje, siguiendo Clean Architecture.

---

## Análisis Previo

### Arquitectura Objetivo
```
apps/trips/
├── domain/
│   ├── models.py              # Trip (entidad pura)
│   └── repositories/
│       └── trip_repository.py # ITripRepository (interface)
├── infrastructure/
│   ├── dependencies.py        # DI para repositorios
│   └── repositories/
│       └── trip_repository.py # TripRepository (MongoDB)
└── api/
    ├── urls.py
    └── versioning/v1/
        ├── views.py           # Endpoints trips
        └── schemas/
            ├── requests.py    # CreateTripRequest
            └── responses.py   # TripResponse
```

---

## Paso 1: Modelo de Dominio

**Archivo**: `apps/trips/domain/models.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional
from enum import Enum

class TripStatus(str, Enum):
    """Estados posibles de un trayecto"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Trip(BaseModel):
    """
    Entidad Trip del dominio
    Representa un trayecto publicado por un conductor
    """
    # Identificador
    id: Optional[str] = None

    # Información básica del trayecto
    origin: str = Field(..., min_length=3, max_length=200)
    destination: str = Field(..., min_length=3, max_length=200)
    departure_date: date
    departure_time: time

    # Coordenadas geográficas (para matching)
    origin_lat: Optional[float] = Field(None, ge=-90, le=90)
    origin_lng: Optional[float] = Field(None, ge=-180, le=180)
    destination_lat: Optional[float] = Field(None, ge=-90, le=90)
    destination_lng: Optional[float] = Field(None, ge=-180, le=180)

    # Gestión de plazas
    available_seats: int = Field(..., ge=0, le=10)
    total_seats: int = Field(..., ge=1, le=10)

    # Motor de Matching (RF-006)
    estimated_arrival_time: Optional[time] = None
    max_detour_minutes: int = Field(default=30, ge=0, le=120)
    current_detour_minutes: int = Field(default=0, ge=0)
    roadmap: list[dict] = Field(default_factory=list)  # Lista de waypoints

    # Conductor
    driver_id: str

    # Metadatos
    status: TripStatus = Field(default=TripStatus.ACTIVE)
    price_per_seat: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)

    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "total_seats": 3,
                "driver_id": "507f1f77bcf86cd799439011",
                "price_per_seat": 5.0,
                "description": "Viaje tranquilo, acepto mascotas"
            }
        }

    def has_available_seats(self) -> bool:
        """Verifica si hay plazas disponibles"""
        return self.available_seats > 0

    def can_accommodate(self, seats_requested: int) -> bool:
        """Verifica si puede acomodar N plazas"""
        return self.available_seats >= seats_requested
```

---

## Paso 2: Interface del Repositorio

**Archivo**: `apps/trips/domain/repositories/trip_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from datetime import date
from apps.trips.domain.models import Trip

class ITripRepository(ABC):
    """Contrato para el repositorio de trayectos"""

    @abstractmethod
    async def create(self, trip: Trip) -> Trip:
        """Crea un nuevo trayecto. Retorna el trayecto con id asignado."""
        pass

    @abstractmethod
    async def get_by_id(self, trip_id: str) -> Optional[Trip]:
        """Obtiene trayecto por ID"""
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> list[Trip]:
        """Lista trayectos con paginación y filtro opcional por estado"""
        pass

    @abstractmethod
    async def get_by_driver(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """Obtiene todos los trayectos de un conductor"""
        pass

    @abstractmethod
    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """Busca trayectos por criterios (para RF-002)"""
        pass

    @abstractmethod
    async def update(self, trip_id: str, trip: Trip) -> bool:
        """Actualiza trayecto. Retorna True si actualizó."""
        pass

    @abstractmethod
    async def delete(self, trip_id: str) -> bool:
        """Elimina trayecto (soft delete)"""
        pass

    @abstractmethod
    async def exists(self, trip_id: str) -> bool:
        """Verifica si un trayecto existe"""
        pass
```

---

## Paso 3: Implementación del Repositorio

**Archivo**: `apps/trips/infrastructure/repositories/trip_repository.py`

```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, date
from typing import Optional
from bson import ObjectId

from apps.trips.domain.models import Trip
from apps.trips.domain.repositories.trip_repository import ITripRepository

class TripRepository(ITripRepository):
    """Implementación MongoDB del repositorio de trayectos"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db["trips"]

    async def create(self, trip: Trip) -> Trip:
        """Crea trayecto en MongoDB"""
        trip_dict = trip.model_dump(exclude={"id"}, mode="json")

        # Convertir date y time a formato MongoDB
        if isinstance(trip_dict.get("departure_date"), date):
            trip_dict["departure_date"] = trip_dict["departure_date"].isoformat()
        if isinstance(trip_dict.get("departure_time"), str):
            pass  # Ya está en string format

        result = await self._collection.insert_one(trip_dict)
        trip.id = str(result.inserted_id)
        return trip

    async def get_by_id(self, trip_id: str) -> Optional[Trip]:
        """Obtiene por ID"""
        try:
            doc = await self._collection.find_one({"_id": ObjectId(trip_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return Trip(**doc)
            return None
        except Exception:
            return None

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> list[Trip]:
        """Lista trayectos con paginación"""
        query = {}
        if status:
            query["status"] = status

        cursor = self._collection.find(query).skip(skip).limit(limit)
        trips = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            trips.append(Trip(**doc))
        return trips

    async def get_by_driver(
        self,
        driver_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """Obtiene trayectos de un conductor"""
        cursor = self._collection.find({"driver_id": driver_id}).skip(skip).limit(limit)
        trips = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            trips.append(Trip(**doc))
        return trips

    async def search(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        date_from: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[Trip]:
        """Busca trayectos por criterios"""
        query = {"status": "active", "is_active": True}

        if origin:
            query["origin"] = {"$regex": origin, "$options": "i"}
        if destination:
            query["destination"] = {"$regex": destination, "$options": "i"}
        if date_from:
            query["departure_date"] = {"$gte": date_from.isoformat()}

        cursor = self._collection.find(query).skip(skip).limit(limit)
        trips = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            trips.append(Trip(**doc))
        return trips

    async def update(self, trip_id: str, trip: Trip) -> bool:
        """Actualiza trayecto"""
        trip.updated_at = datetime.utcnow()
        update_dict = trip.model_dump(exclude={"id", "created_at"}, mode="json")

        result = await self._collection.update_one(
            {"_id": ObjectId(trip_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0

    async def delete(self, trip_id: str) -> bool:
        """Soft delete"""
        result = await self._collection.update_one(
            {"_id": ObjectId(trip_id)},
            {"$set": {"is_active": False, "status": "cancelled", "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def exists(self, trip_id: str) -> bool:
        """Verifica existencia"""
        try:
            count = await self._collection.count_documents({"_id": ObjectId(trip_id)})
            return count > 0
        except Exception:
            return False
```

---

## Paso 4: Dependency Injection

**Archivo**: `apps/trips/infrastructure/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.database import get_database
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.repositories.trip_repository import TripRepository

async def get_trip_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> ITripRepository:
    """Inyecta repositorio de trayectos"""
    return TripRepository(db)
```

---

## Paso 5: DTOs (Schemas)

**Archivo**: `apps/trips/api/versioning/v1/schemas/requests.py`

```python
from pydantic import BaseModel, Field
from datetime import date, time
from typing import Optional

class CreateTripRequest(BaseModel):
    """Schema para crear trayecto"""
    origin: str = Field(..., min_length=3, max_length=200)
    destination: str = Field(..., min_length=3, max_length=200)
    departure_date: date = Field(..., description="Fecha del viaje (YYYY-MM-DD)")
    departure_time: time = Field(..., description="Hora de salida (HH:MM:SS)")
    available_seats: int = Field(..., ge=1, le=10, description="Plazas disponibles")

    # Opcionales
    price_per_seat: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    max_detour_minutes: int = Field(default=30, ge=0, le=120, description="Desvío máximo permitido")
    estimated_arrival_time: Optional[time] = None

    class Config:
        json_schema_extra = {
            "example": {
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "price_per_seat": 5.0,
                "description": "Viaje tranquilo",
                "max_detour_minutes": 30
            }
        }

class UpdateTripRequest(BaseModel):
    """Schema para actualizar trayecto"""
    available_seats: Optional[int] = Field(None, ge=0, le=10)
    price_per_seat: Optional[float] = Field(None, ge=0)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
```

**Archivo**: `apps/trips/api/versioning/v1/schemas/responses.py`

```python
from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional

class TripResponse(BaseModel):
    """Schema de respuesta de trayecto"""
    id: str
    origin: str
    destination: str
    departure_date: date
    departure_time: time
    available_seats: int
    total_seats: int
    driver_id: str
    status: str

    # Opcionales
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    estimated_arrival_time: Optional[time] = None
    max_detour_minutes: int
    current_detour_minutes: int
    price_per_seat: Optional[float] = None
    description: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

class TripListResponse(BaseModel):
    """Schema de respuesta para lista de trayectos"""
    trips: list[TripResponse]
    total: int
    skip: int
    limit: int
```

---

## Paso 6: Endpoints (Views)

**Archivo**: `apps/trips/api/versioning/v1/views.py`

```python
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.trips.domain.models import Trip
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_trip_repository
from apps.trips.api.versioning/v1.schemas.requests import CreateTripRequest, UpdateTripRequest
from apps.trips.api.versioning.v1.schemas.responses import TripResponse, TripListResponse

# Importar autenticación de users
from apps.users.infrastructure.dependencies import get_current_user
from apps.users.domain.models import User, UserRole

router = APIRouter()

@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    payload: CreateTripRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Publicar nuevo trayecto.

    **Requisitos:**
    - Usuario autenticado
    - Usuario debe tener rol de conductor
    - Todos los campos requeridos presentes
    - Fecha debe ser futura

    **Reglas de Negocio:**
    - available_seats > 0
    - departure_date >= hoy
    """
    # Validar rol de conductor
    if current_user.role not in [UserRole.DRIVER, UserRole.BOTH]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los conductores pueden publicar trayectos"
        )

    # Validar fecha futura (opcional pero recomendado)
    from datetime import date as dt_date
    if payload.departure_date < dt_date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha del trayecto debe ser futura"
        )

    # Crear entidad de dominio
    trip = Trip(
        origin=payload.origin,
        destination=payload.destination,
        departure_date=payload.departure_date,
        departure_time=payload.departure_time,
        available_seats=payload.available_seats,
        total_seats=payload.available_seats,  # Inicialmente son iguales
        driver_id=current_user.id,
        price_per_seat=payload.price_per_seat,
        description=payload.description,
        max_detour_minutes=payload.max_detour_minutes,
        estimated_arrival_time=payload.estimated_arrival_time
    )

    # Guardar en BD
    created_trip = await repo.create(trip)

    return TripResponse(**created_trip.model_dump())

@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: str,
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Obtener trayecto por ID.

    - No requiere autenticación (búsqueda pública)
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trayecto no encontrado"
        )

    return TripResponse(**trip.model_dump())

@router.get("/", response_model=TripListResponse)
async def list_trips(
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filtrar por estado")
):
    """
    Listar todos los trayectos con paginación.

    - No requiere autenticación
    - Soporta filtro por estado
    """
    trips = await repo.get_all(skip=skip, limit=limit, status=status)

    return TripListResponse(
        trips=[TripResponse(**t.model_dump()) for t in trips],
        total=len(trips),  # TODO: Implementar count real
        skip=skip,
        limit=limit
    )

@router.get("/driver/{driver_id}", response_model=TripListResponse)
async def list_trips_by_driver(
    driver_id: str,
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Listar trayectos de un conductor específico.
    """
    trips = await repo.get_by_driver(driver_id, skip=skip, limit=limit)

    return TripListResponse(
        trips=[TripResponse(**t.model_dump()) for t in trips],
        total=len(trips),
        skip=skip,
        limit=limit
    )

@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: str,
    payload: UpdateTripRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Actualizar trayecto existente.

    **Requisitos:**
    - Usuario autenticado
    - Solo el conductor propietario puede actualizar
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trayecto no encontrado"
        )

    # Verificar propiedad
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el conductor propietario puede actualizar el trayecto"
        )

    # Actualizar solo campos proporcionados
    if payload.available_seats is not None:
        trip.available_seats = payload.available_seats
    if payload.price_per_seat is not None:
        trip.price_per_seat = payload.price_per_seat
    if payload.description is not None:
        trip.description = payload.description
    if payload.status is not None:
        trip.status = payload.status

    success = await repo.update(trip_id, trip)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar trayecto"
        )

    return TripResponse(**trip.model_dump())

@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Eliminar (cancelar) trayecto.

    **Requisitos:**
    - Usuario autenticado
    - Solo el conductor propietario puede eliminar
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trayecto no encontrado"
        )

    # Verificar propiedad
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el conductor propietario puede eliminar el trayecto"
        )

    success = await repo.delete(trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar trayecto"
        )

    return None
```

---

## Paso 7: Registrar Router

**Archivo**: `apps/trips/api/urls.py`

```python
from fastapi import APIRouter
from apps.trips.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1", tags=["Trips"])
```

**Actualizar**: `main.py`

```python
from apps.trips.api.urls import router as trips_router

# En la sección de routers
app.include_router(trips_router, prefix="/api/v1/trips", tags=["Trips"])
```

---

## Paso 8: Crear Índices en MongoDB

**Archivo**: `scripts/create_indexes.py` (crear si no existe)

```python
"""Script para crear índices en MongoDB"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings

async def create_trip_indexes():
    """Crea índices para la colección trips"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Índice para búsqueda por origen/destino
    await db.trips.create_index([("origin", 1), ("destination", 1)])

    # Índice para búsqueda por fecha
    await db.trips.create_index([("departure_date", 1)])

    # Índice para filtrar activos
    await db.trips.create_index([("status", 1), ("is_active", 1)])

    # Índice para trayectos de conductor
    await db.trips.create_index([("driver_id", 1)])

    # Índice geoespacial (para matching futuro)
    await db.trips.create_index([("origin_lat", 1), ("origin_lng", 1)])
    await db.trips.create_index([("destination_lat", 1), ("destination_lng", 1)])

    print("✅ Índices de trips creados exitosamente")

    client.close()

if __name__ == "__main__":
    asyncio.run(create_trip_indexes())
```

Ejecutar:
```bash
poetry run python scripts/create_indexes.py
```

---

## Paso 9: Testing

**Archivo**: `tests/test_trips/test_create_trip.py`

```python
import pytest
from httpx import AsyncClient
from datetime import date, time
from main import app

@pytest.mark.asyncio
async def test_create_trip_success(auth_token):
    """Test creación exitosa de trayecto"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/trips/v1/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3,
                "price_per_seat": 5.0
            }
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["origin"] == "Cádiz"
    assert data["available_seats"] == 3

@pytest.mark.asyncio
async def test_create_trip_without_auth():
    """Test creación sin autenticación"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/trips/v1/",
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2025-12-15",
                "departure_time": "09:00:00",
                "available_seats": 3
            }
        )

    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_trip_past_date(auth_token):
    """Test creación con fecha pasada"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/trips/v1/",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "origin": "Cádiz",
                "destination": "Sevilla",
                "departure_date": "2020-01-01",
                "departure_time": "09:00:00",
                "available_seats": 3
            }
        )

    assert response.status_code == 400
    assert "futura" in response.json()["detail"].lower()
```

---

## Checklist de Implementación

- [ ] Crear estructura de carpetas para módulo trips
- [ ] Modelo Trip en domain/models.py con todos los campos
- [ ] Interface ITripRepository en domain/repositories/
- [ ] Implementación TripRepository en infrastructure/repositories/
- [ ] Dependency injection en infrastructure/dependencies.py
- [ ] Schemas de request/response en api/.../schemas/
- [ ] Endpoints en api/versioning/v1/views.py:
  - [ ] POST / (crear trayecto)
  - [ ] GET /{trip_id} (obtener trayecto)
  - [ ] GET / (listar trayectos)
  - [ ] GET /driver/{driver_id} (trayectos de conductor)
  - [ ] PUT /{trip_id} (actualizar trayecto)
  - [ ] DELETE /{trip_id} (eliminar trayecto)
- [ ] Router registrado en main.py
- [ ] Crear índices en MongoDB
- [ ] Tests unitarios (crear, obtener, listar)
- [ ] Verificar en /docs (Swagger)
- [ ] Validar autenticación en endpoints protegidos
- [ ] Validar que solo conductores pueden publicar

---

## Verificación

```bash
# Iniciar servidor
poetry run python main.py

# Probar creación de trayecto (necesita token)
curl -X POST http://localhost:8000/api/v1/trips/v1/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-15",
    "departure_time": "09:00:00",
    "available_seats": 3,
    "price_per_seat": 5.0
  }'

# Listar trayectos (público)
curl http://localhost:8000/api/v1/trips/v1/

# Ver documentación
open http://localhost:8000/docs
```

---

## Próximo Paso

Una vez completado RF-001, proceder con:
- **RF-002**: Búsqueda de Trayectos (usa search method del repositorio)
