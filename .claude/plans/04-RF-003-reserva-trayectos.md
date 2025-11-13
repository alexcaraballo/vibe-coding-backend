# Plan: RF-003 - Reserva de Trayectos

**Issue**: #3
**Prioridad**: ALTA (Core MVP)
**Estimación**: 4-5 horas
**Dependencias**:
- 02-RF-001-publicacion-trayectos.md (completado)
- 03-RF-002-busqueda-trayectos.md (completado)

---

## Objetivo

Permitir a los pasajeros reservar un lugar en un trayecto publicado, implementando validación de disponibilidad (RF-INF-002) y gestión automática de plazas (RF-INF-004), siguiendo Clean Architecture.

---

## Análisis Previo

### Arquitectura Objetivo
```
apps/trips/
├── domain/
│   ├── models.py              # Añadir Booking
│   └── repositories/
│       └── booking_repository.py # IBookingRepository
├── infrastructure/
│   ├── dependencies.py        # Añadir booking DI
│   ├── services/
│   │   └── booking_service.py # Lógica de reserva
│   └── repositories/
│       └── booking_repository.py # BookingRepository (MongoDB)
└── api/
    └── versioning/v1/
        ├── views.py           # Añadir endpoints booking
        └── schemas/
            ├── requests.py    # BookTripRequest
            └── responses.py   # BookingResponse
```

### Funcionalidades incluidas
✅ RF-003: Reserva de Trayectos
✅ RF-INF-002: Validación de Disponibilidad
✅ RF-INF-004: Gestión de Plazas

---

## Paso 1: Modelo de Dominio - Booking

**Archivo**: `apps/trips/domain/models.py`

Agregar al final del archivo:

```python
class BookingStatus(str, Enum):
    """Estados posibles de una reserva"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Booking(BaseModel):
    """
    Entidad Booking del dominio
    Representa una reserva de un pasajero en un trayecto
    """
    # Identificador
    id: Optional[str] = None

    # Relaciones
    trip_id: str
    passenger_id: str

    # Detalles de la reserva
    seats_booked: int = Field(default=1, ge=1, le=10)
    status: BookingStatus = Field(default=BookingStatus.CONFIRMED)

    # Información adicional
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    passenger_notes: Optional[str] = Field(None, max_length=500)

    # Metadatos
    booking_date: datetime = Field(default_factory=datetime.utcnow)
    cancellation_date: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trip_id": "507f1f77bcf86cd799439011",
                "passenger_id": "507f1f77bcf86cd799439012",
                "seats_booked": 1,
                "status": "confirmed",
                "passenger_notes": "Llegaré puntual"
            }
        }

    def can_be_cancelled(self) -> bool:
        """Verifica si la reserva puede ser cancelada"""
        return self.status == BookingStatus.CONFIRMED and self.is_active

    def cancel(self):
        """Cancela la reserva"""
        self.status = BookingStatus.CANCELLED
        self.is_active = False
        self.cancellation_date = datetime.utcnow()
```

---

## Paso 2: Interface del Repositorio - Booking

**Archivo**: `apps/trips/domain/repositories/booking_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.trips.domain.models import Booking

class IBookingRepository(ABC):
    """Contrato para el repositorio de reservas"""

    @abstractmethod
    async def create(self, booking: Booking) -> Booking:
        """Crea una nueva reserva. Retorna la reserva con id asignado."""
        pass

    @abstractmethod
    async def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Obtiene reserva por ID"""
        pass

    @abstractmethod
    async def get_by_trip(
        self,
        trip_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Obtiene todas las reservas de un trayecto"""
        pass

    @abstractmethod
    async def get_by_passenger(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Obtiene todas las reservas de un pasajero"""
        pass

    @abstractmethod
    async def exists_active_booking(
        self,
        trip_id: str,
        passenger_id: str
    ) -> bool:
        """Verifica si el pasajero ya tiene una reserva activa en el trayecto"""
        pass

    @abstractmethod
    async def update(self, booking_id: str, booking: Booking) -> bool:
        """Actualiza reserva. Retorna True si actualizó."""
        pass

    @abstractmethod
    async def delete(self, booking_id: str) -> bool:
        """Elimina reserva (soft delete)"""
        pass

    @abstractmethod
    async def count_by_trip(self, trip_id: str) -> int:
        """Cuenta reservas activas de un trayecto"""
        pass
```

---

## Paso 3: Implementación del Repositorio - Booking

**Archivo**: `apps/trips/infrastructure/repositories/booking_repository.py`

```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
from bson import ObjectId

from apps.trips.domain.models import Booking
from apps.trips.domain.repositories.booking_repository import IBookingRepository

class BookingRepository(IBookingRepository):
    """Implementación MongoDB del repositorio de reservas"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db["bookings"]

    async def create(self, booking: Booking) -> Booking:
        """Crea reserva en MongoDB"""
        booking_dict = booking.model_dump(exclude={"id"}, mode="json")
        result = await self._collection.insert_one(booking_dict)
        booking.id = str(result.inserted_id)
        return booking

    async def get_by_id(self, booking_id: str) -> Optional[Booking]:
        """Obtiene por ID"""
        try:
            doc = await self._collection.find_one({"_id": ObjectId(booking_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return Booking(**doc)
            return None
        except Exception:
            return None

    async def get_by_trip(
        self,
        trip_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Obtiene reservas de un trayecto"""
        cursor = self._collection.find({
            "trip_id": trip_id,
            "is_active": True
        }).skip(skip).limit(limit)

        bookings = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            bookings.append(Booking(**doc))
        return bookings

    async def get_by_passenger(
        self,
        passenger_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Booking]:
        """Obtiene reservas de un pasajero"""
        cursor = self._collection.find({
            "passenger_id": passenger_id,
            "is_active": True
        }).skip(skip).limit(limit).sort("booking_date", -1)

        bookings = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            bookings.append(Booking(**doc))
        return bookings

    async def exists_active_booking(
        self,
        trip_id: str,
        passenger_id: str
    ) -> bool:
        """Verifica reserva duplicada"""
        count = await self._collection.count_documents({
            "trip_id": trip_id,
            "passenger_id": passenger_id,
            "is_active": True,
            "status": {"$in": ["pending", "confirmed"]}
        })
        return count > 0

    async def update(self, booking_id: str, booking: Booking) -> bool:
        """Actualiza reserva"""
        booking.updated_at = datetime.utcnow()
        update_dict = booking.model_dump(exclude={"id", "created_at"}, mode="json")

        result = await self._collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0

    async def delete(self, booking_id: str) -> bool:
        """Soft delete"""
        result = await self._collection.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": {
                "is_active": False,
                "status": "cancelled",
                "cancellation_date": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        return result.modified_count > 0

    async def count_by_trip(self, trip_id: str) -> int:
        """Cuenta reservas activas"""
        return await self._collection.count_documents({
            "trip_id": trip_id,
            "is_active": True,
            "status": {"$in": ["confirmed", "pending"]}
        })
```

---

## Paso 4: Servicio de Reserva con Lógica de Negocio

**Archivo**: `apps/trips/infrastructure/services/booking_service.py`

```python
from typing import Optional
from fastapi import HTTPException, status

from apps.trips.domain.models import Booking, Trip
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from shared.exceptions import InsufficientSeats, ValidationError

class BookingService:
    """
    Servicio de lógica de negocio para reservas
    Implementa RF-INF-002 (Validación) y RF-INF-004 (Gestión de Plazas)
    """

    def __init__(
        self,
        booking_repo: IBookingRepository,
        trip_repo: ITripRepository
    ):
        self.booking_repo = booking_repo
        self.trip_repo = trip_repo

    async def create_booking(
        self,
        trip_id: str,
        passenger_id: str,
        seats_requested: int = 1,
        passenger_notes: Optional[str] = None
    ) -> Booking:
        """
        Crea una reserva con validaciones completas.

        RF-INF-002: Validación de Disponibilidad
        RF-INF-004: Gestión de Plazas
        """
        # 1. Validar que el trayecto existe
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trayecto no encontrado"
            )

        # 2. Validar que el trayecto está activo
        if trip.status != "active" or not trip.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El trayecto no está disponible"
            )

        # 3. RF-INF-002: Validar disponibilidad de plazas
        if not trip.can_accommodate(seats_requested):
            raise InsufficientSeats()

        # 4. Validar que el pasajero no es el conductor
        if trip.driver_id == passenger_id:
            raise ValidationError("El conductor no puede reservar su propio trayecto")

        # 5. Validar que no hay reserva duplicada
        has_booking = await self.booking_repo.exists_active_booking(trip_id, passenger_id)
        if has_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya tienes una reserva activa en este trayecto"
            )

        # 6. Validar número de plazas solicitadas
        if seats_requested < 1 or seats_requested > trip.available_seats:
            raise ValidationError(f"Número de plazas inválido. Disponibles: {trip.available_seats}")

        # 7. Crear la reserva
        booking = Booking(
            trip_id=trip_id,
            passenger_id=passenger_id,
            seats_booked=seats_requested,
            passenger_notes=passenger_notes
        )

        created_booking = await self.booking_repo.create(booking)

        # 8. RF-INF-004: Actualizar plazas disponibles del trayecto
        trip.available_seats -= seats_requested
        await self.trip_repo.update(trip_id, trip)

        return created_booking

    async def cancel_booking(self, booking_id: str, user_id: str) -> bool:
        """
        Cancela una reserva y libera las plazas (RF-INF-003).

        RF-INF-004: Gestión de Plazas (incrementar al cancelar)
        """
        # 1. Obtener la reserva
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva no encontrada"
            )

        # 2. Validar que el usuario es el dueño de la reserva
        if booking.passenger_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes cancelar reservas de otros usuarios"
            )

        # 3. Validar que la reserva puede ser cancelada
        if not booking.can_be_cancelled():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta reserva no puede ser cancelada"
            )

        # 4. Obtener el trayecto
        trip = await self.trip_repo.get_by_id(booking.trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trayecto asociado no encontrado"
            )

        # 5. Cancelar la reserva
        booking.cancel()
        await self.booking_repo.update(booking_id, booking)

        # 6. RF-INF-004: Liberar plazas
        trip.available_seats += booking.seats_booked
        await self.trip_repo.update(booking.trip_id, trip)

        return True
```

---

## Paso 5: Dependency Injection - Booking

**Archivo**: `apps/trips/infrastructure/dependencies.py`

Agregar:

```python
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.infrastructure.repositories.booking_repository import BookingRepository
from apps.trips.infrastructure.services.booking_service import BookingService

async def get_booking_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> IBookingRepository:
    """Inyecta repositorio de reservas"""
    return BookingRepository(db)

async def get_booking_service(
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
) -> BookingService:
    """Inyecta servicio de reservas"""
    return BookingService(booking_repo, trip_repo)
```

---

## Paso 6: DTOs - Booking

**Archivo**: `apps/trips/api/versioning/v1/schemas/requests.py`

Agregar:

```python
class BookTripRequest(BaseModel):
    """Schema para reservar trayecto"""
    seats_requested: int = Field(default=1, ge=1, le=10, description="Número de plazas a reservar")
    passenger_notes: Optional[str] = Field(None, max_length=500, description="Notas adicionales")
    pickup_location: Optional[str] = Field(None, max_length=200, description="Punto de recogida específico")
    dropoff_location: Optional[str] = Field(None, max_length=200, description="Punto de bajada específico")

    class Config:
        json_schema_extra = {
            "example": {
                "seats_requested": 1,
                "passenger_notes": "Llegaré 5 minutos antes"
            }
        }
```

**Archivo**: `apps/trips/api/versioning/v1/schemas/responses.py`

Agregar:

```python
from apps.trips.domain.models import BookingStatus

class BookingResponse(BaseModel):
    """Schema de respuesta de reserva"""
    id: str
    trip_id: str
    passenger_id: str
    seats_booked: int
    status: str
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None
    passenger_notes: Optional[str] = None
    booking_date: datetime
    is_active: bool
    created_at: datetime

class BookingWithTripResponse(BaseModel):
    """Schema de respuesta de reserva con información del trayecto"""
    booking: BookingResponse
    trip: TripResponse

class BookingListResponse(BaseModel):
    """Schema de respuesta para lista de reservas"""
    bookings: list[BookingResponse]
    total: int
    skip: int
    limit: int
```

---

## Paso 7: Endpoints - Booking

**Archivo**: `apps/trips/api/versioning/v1/views.py`

Agregar al final:

```python
from apps.trips.infrastructure.services.booking_service import BookingService
from apps.trips.infrastructure.dependencies import get_booking_service, get_booking_repository
from apps.trips.api.versioning.v1.schemas.responses import (
    BookingResponse,
    BookingWithTripResponse,
    BookingListResponse
)

# ============= BOOKING ENDPOINTS =============

@router.post("/{trip_id}/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def book_trip(
    trip_id: str,
    payload: BookTripRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)]
):
    """
    Reservar plaza en un trayecto.

    **Endpoint:** `POST /trips/{trip_id}/book`

    **Requisitos:**
    - Usuario autenticado
    - Trayecto debe existir y estar activo
    - Debe haber plazas disponibles
    - Usuario no puede ser el conductor
    - No puede tener reserva duplicada

    **Proceso:**
    1. Valida disponibilidad (RF-INF-002)
    2. Crea la reserva
    3. Decrementa plazas disponibles (RF-INF-004)
    4. Añade pasajero a lista del trayecto

    **Reglas de Negocio:**
    - available_seats >= seats_requested
    - conductor != pasajero
    - Sin reservas duplicadas
    - Transacción atómica (reserva + actualización de plazas)
    """
    created_booking = await booking_service.create_booking(
        trip_id=trip_id,
        passenger_id=current_user.id,
        seats_requested=payload.seats_requested,
        passenger_notes=payload.passenger_notes
    )

    return BookingResponse(**created_booking.model_dump())

@router.get("/bookings/{booking_id}", response_model=BookingWithTripResponse)
async def get_booking(
    booking_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Obtener detalles de una reserva con información del trayecto.

    **Requisitos:**
    - Usuario autenticado
    - Solo el pasajero o el conductor pueden ver la reserva
    """
    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada"
        )

    # Obtener trayecto asociado
    trip = await trip_repo.get_by_id(booking.trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trayecto asociado no encontrado"
        )

    # Validar acceso (pasajero o conductor)
    if booking.passenger_id != current_user.id and trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta reserva"
        )

    return BookingWithTripResponse(
        booking=BookingResponse(**booking.model_dump()),
        trip=TripResponse(**trip.model_dump())
    )

@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)]
):
    """
    Cancelar reserva (RF-INF-003).

    **Proceso:**
    1. Valida que la reserva existe
    2. Valida que el usuario es el dueño
    3. Cancela la reserva
    4. Libera las plazas (RF-INF-004)
    """
    await booking_service.cancel_booking(booking_id, current_user.id)
    return None

@router.get("/{trip_id}/bookings", response_model=BookingListResponse)
async def list_trip_bookings(
    trip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Listar reservas de un trayecto.

    **Requisitos:**
    - Usuario autenticado
    - Solo el conductor del trayecto puede ver todas las reservas
    """
    # Verificar que el trayecto existe
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trayecto no encontrado"
        )

    # Verificar que el usuario es el conductor
    if trip.driver_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el conductor puede ver las reservas del trayecto"
        )

    bookings = await booking_repo.get_by_trip(trip_id, skip=skip, limit=limit)

    return BookingListResponse(
        bookings=[BookingResponse(**b.model_dump()) for b in bookings],
        total=len(bookings),
        skip=skip,
        limit=limit
    )
```

---

## Paso 8: Crear Excepciones Customizadas

**Archivo**: `shared/exceptions.py` (actualizar)

Ya existe, agregar si falta:

```python
class InsufficientSeats(DomainException):
    """No hay plazas disponibles"""
    def __init__(self):
        super().__init__(
            message="No hay plazas disponibles en este trayecto",
            code="INSUFFICIENT_SEATS"
        )
```

---

## Paso 9: Crear Índices para Bookings

**Archivo**: `scripts/create_indexes.py`

Agregar:

```python
async def create_booking_indexes():
    """Crea índices para la colección bookings"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Índice para obtener reservas por trayecto
    await db.bookings.create_index([("trip_id", 1)])

    # Índice para obtener reservas por pasajero
    await db.bookings.create_index([("passenger_id", 1)])

    # Índice compuesto para detectar duplicados
    await db.bookings.create_index([
        ("trip_id", 1),
        ("passenger_id", 1),
        ("is_active", 1)
    ])

    # Índice para filtrar activas
    await db.bookings.create_index([("status", 1), ("is_active", 1)])

    print("✅ Índices de bookings creados exitosamente")

    client.close()
```

---

## Paso 10: Testing

**Archivo**: `tests/test_trips/test_booking.py`

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_book_trip_success(auth_token, trip_id):
    """Test reserva exitosa"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/trips/v1/{trip_id}/book",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"seats_requested": 1}
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["trip_id"] == trip_id
    assert data["seats_booked"] == 1

@pytest.mark.asyncio
async def test_book_trip_insufficient_seats(auth_token, trip_id):
    """Test reserva sin plazas disponibles"""
    # Reservar todas las plazas primero...

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/trips/v1/{trip_id}/book",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"seats_requested": 10}  # Más de las disponibles
        )

    assert response.status_code == 400
    assert "plazas" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_book_trip_duplicate(auth_token, trip_id):
    """Test reserva duplicada"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Primera reserva
        await ac.post(
            f"/api/v1/trips/v1/{trip_id}/book",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"seats_requested": 1}
        )

        # Intentar segunda reserva
        response = await ac.post(
            f"/api/v1/trips/v1/{trip_id}/book",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"seats_requested": 1}
        )

    assert response.status_code == 400
    assert "duplicada" in response.json()["detail"].lower() or "ya tienes" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_cancel_booking_success(auth_token, booking_id):
    """Test cancelación exitosa"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(
            f"/api/v1/trips/v1/bookings/{booking_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 204
```

---

## Checklist de Implementación

- [ ] Crear modelo Booking en domain/models.py
- [ ] Crear interface IBookingRepository
- [ ] Implementar BookingRepository (MongoDB)
- [ ] Crear BookingService con lógica de negocio:
  - [ ] RF-INF-002: Validación de disponibilidad
  - [ ] RF-INF-004: Gestión de plazas (decrementar/incrementar)
  - [ ] Validación de reservas duplicadas
  - [ ] Validación conductor != pasajero
- [ ] Dependency injection para booking
- [ ] Schemas de request/response
- [ ] Endpoints:
  - [ ] POST /{trip_id}/book (reservar)
  - [ ] GET /bookings/{booking_id} (obtener reserva)
  - [ ] DELETE /bookings/{booking_id} (cancelar)
  - [ ] GET /{trip_id}/bookings (listar reservas del trayecto)
- [ ] Crear índices en MongoDB
- [ ] Tests:
  - [ ] Reserva exitosa
  - [ ] Sin plazas disponibles
  - [ ] Reserva duplicada
  - [ ] Conductor no puede reservar su trayecto
  - [ ] Cancelación exitosa
  - [ ] Liberación de plazas al cancelar
- [ ] Verificar en /docs

---

## Verificación

```bash
# Reservar trayecto (necesita token)
curl -X POST http://localhost:8000/api/v1/trips/v1/<TRIP_ID>/book \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"seats_requested": 1, "passenger_notes": "Llegaré puntual"}'

# Obtener reserva
curl http://localhost:8000/api/v1/trips/v1/bookings/<BOOKING_ID> \
  -H "Authorization: Bearer <TOKEN>"

# Cancelar reserva
curl -X DELETE http://localhost:8000/api/v1/trips/v1/bookings/<BOOKING_ID> \
  -H "Authorization: Bearer <TOKEN>"

# Listar reservas de un trayecto (solo conductor)
curl http://localhost:8000/api/v1/trips/v1/<TRIP_ID>/bookings \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Criterios de Aceptación

✅ **RF-003: Reserva de Trayectos**
- Pasajero puede reservar plaza en trayecto disponible
- Sistema decrementa plazas disponibles
- Sistema añade pasajero a lista del trayecto
- Confirmación de reserva

✅ **RF-INF-002: Validación de Disponibilidad**
- Verifica plazas disponibles antes de confirmar
- Previene overbooking
- Validación de trayecto activo
- Validación de reservas duplicadas

✅ **RF-INF-004: Gestión de Plazas**
- Actualización automática de plazas disponibles
- Decremento al reservar
- Incremento al cancelar
- Control de capacidad máxima

✅ **RF-INF-003: Cancelación de Reservas**
- Permitir cancelar reservas
- Liberar plazas canceladas
- Actualizar estado de reserva

---

## Próximo Paso

Una vez completado RF-003 (incluye RF-INF-002, RF-INF-003, RF-INF-004), proceder con:
- **RF-004**: Listado de Reservas de Usuario
