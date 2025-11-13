# Plan: RF-004 - Listado de Reservas de Usuario

**Issue**: #4
**Prioridad**: ALTA (Core MVP)
**Estimación**: 1-2 horas
**Dependencias**: 04-RF-003-reserva-trayectos.md (completado)

---

## Objetivo

Permitir a un usuario consultar todas sus reservas con información completa del trayecto y conductor, implementando endpoints para gestionar el historial de viajes.

---

## Análisis Previo

### Infraestructura Existente (de RF-003)
✅ Modelo `Booking` ya implementado
✅ Repositorio `IBookingRepository` con método `get_by_passenger()`
✅ Implementación `BookingRepository` en MongoDB
✅ Schemas de respuesta `BookingResponse`, `BookingWithTripResponse`

### Lo que falta
❌ Endpoint específico `GET /users/{id}/bookings`
❌ Endpoint en módulo users (opción alternativa)
❌ Schema enriquecido con información de conductor
❌ Filtros por estado de reserva

---

## Paso 1: Endpoint en Users Module

**Opción 1**: Agregar endpoint en `apps/users/api/versioning/v1/views.py`

```python
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import get_booking_repository, get_trip_repository
from apps.trips.api.versioning.v1.schemas.responses import BookingWithTripResponse

@router.get("/{user_id}/bookings", response_model=list[BookingWithTripResponse])
async def get_user_bookings(
    user_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filtrar por estado: confirmed, cancelled, completed")
):
    """
    Listar todas las reservas de un usuario.

    **Endpoint:** `GET /users/{id}/bookings`

    **Requisitos:**
    - Usuario autenticado
    - Solo el usuario dueño puede ver sus propias reservas

    **Características:**
    - Incluye información completa del trayecto
    - Incluye información del conductor
    - Filtros por estado
    - Paginación
    - Ordenado por fecha (más recientes primero)
    """
    # Validar que el usuario existe
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Validar que el usuario autenticado puede ver estas reservas
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes ver tus propias reservas"
        )

    # Obtener reservas del usuario
    bookings = await booking_repo.get_by_passenger(user_id, skip=skip, limit=limit)

    # Filtrar por estado si se proporciona
    if status:
        bookings = [b for b in bookings if b.status == status]

    # Enriquecer con información de trayectos y conductores
    result = []
    for booking in bookings:
        trip = await trip_repo.get_by_id(booking.trip_id)
        if trip:
            # Obtener información del conductor
            driver = await user_repo.get_by_id(trip.driver_id)

            result.append(BookingWithTripResponse(
                booking=BookingResponse(**booking.model_dump()),
                trip=TripResponse(**trip.model_dump()),
                driver=UserResponse(**driver.model_dump()) if driver else None
            ))

    return result
```

---

## Paso 2: Schema Enriquecido con Conductor

**Archivo**: `apps/trips/api/versioning/v1/schemas/responses.py`

Actualizar `BookingWithTripResponse`:

```python
class BookingWithTripResponse(BaseModel):
    """
    Schema de respuesta de reserva con información completa.
    Incluye trayecto y conductor.
    """
    booking: BookingResponse
    trip: TripResponse
    driver: Optional[UserResponse] = None  # Información del conductor

    class Config:
        json_schema_extra = {
            "example": {
                "booking": {
                    "id": "507f1f77bcf86cd799439011",
                    "trip_id": "507f1f77bcf86cd799439012",
                    "passenger_id": "507f1f77bcf86cd799439013",
                    "seats_booked": 1,
                    "status": "confirmed",
                    "booking_date": "2025-12-10T10:00:00Z"
                },
                "trip": {
                    "id": "507f1f77bcf86cd799439012",
                    "origin": "Cádiz",
                    "destination": "Sevilla",
                    "departure_date": "2025-12-15",
                    "departure_time": "09:00:00"
                },
                "driver": {
                    "id": "507f1f77bcf86cd799439014",
                    "name": "Juan Pérez",
                    "email": "juan@example.com"
                }
            }
        }
```

---

## Paso 3: Opción 2 - Endpoint en Trips Module

**Archivo**: `apps/trips/api/versioning/v1/views.py`

Alternativa más simple (ya existe parcialmente en RF-003):

```python
@router.get("/my-bookings", response_model=list[BookingWithTripResponse])
async def get_my_bookings(
    current_user: Annotated[User, Depends(get_current_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None)
):
    """
    Obtener mis reservas (del usuario autenticado).

    **Endpoint:** `GET /trips/my-bookings`

    **Características:**
    - Acceso directo a reservas del usuario autenticado
    - No requiere especificar user_id (se obtiene del token)
    - Incluye información del trayecto y conductor
    """
    bookings = await booking_repo.get_by_passenger(
        current_user.id,
        skip=skip,
        limit=limit
    )

    if status:
        bookings = [b for b in bookings if b.status == status]

    result = []
    for booking in bookings:
        trip = await trip_repo.get_by_id(booking.trip_id)
        if trip:
            driver = await user_repo.get_by_id(trip.driver_id)
            result.append(BookingWithTripResponse(
                booking=BookingResponse(**booking.model_dump()),
                trip=TripResponse(**trip.model_dump()),
                driver=UserResponse(**driver.model_dump()) if driver else None
            ))

    return result
```

---

## Paso 4: Mejorar Repositorio con Filtros

**Archivo**: `apps/trips/infrastructure/repositories/booking_repository.py`

Mejorar método `get_by_passenger`:

```python
async def get_by_passenger(
    self,
    passenger_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> list[Booking]:
    """
    Obtiene reservas de un pasajero con filtro opcional por estado.
    Ordenadas por fecha de reserva (más recientes primero).
    """
    query = {
        "passenger_id": passenger_id,
        "is_active": True
    }

    if status:
        query["status"] = status

    cursor = self._collection.find(query).sort("booking_date", -1).skip(skip).limit(limit)

    bookings = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        bookings.append(Booking(**doc))
    return bookings
```

Actualizar la interface también:

**Archivo**: `apps/trips/domain/repositories/booking_repository.py`

```python
@abstractmethod
async def get_by_passenger(
    self,
    passenger_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> list[Booking]:
    """Obtiene todas las reservas de un pasajero con filtro opcional"""
    pass
```

---

## Paso 5: Testing

**Archivo**: `tests/test_users/test_user_bookings.py`

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_get_user_bookings_success(auth_token, user_id):
    """Test obtener reservas de usuario"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/users/v1/{user_id}/bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Verificar estructura
    if len(data) > 0:
        assert "booking" in data[0]
        assert "trip" in data[0]
        assert "driver" in data[0]

@pytest.mark.asyncio
async def test_get_my_bookings(auth_token):
    """Test obtener mis reservas (usuario autenticado)"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/trips/v1/my-bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_user_bookings_other_user(auth_token, other_user_id):
    """Test no puede ver reservas de otro usuario"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/users/v1/{other_user_id}/bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_user_bookings_with_status_filter(auth_token, user_id):
    """Test filtrar reservas por estado"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/users/v1/{user_id}/bookings?status=confirmed",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    # Verificar que todas son confirmed
    for item in data:
        assert item["booking"]["status"] == "confirmed"

@pytest.mark.asyncio
async def test_get_user_bookings_pagination(auth_token, user_id):
    """Test paginación de reservas"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/users/v1/{user_id}/bookings?skip=0&limit=5",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5

@pytest.mark.asyncio
async def test_get_user_bookings_empty(auth_token, user_without_bookings_id):
    """Test usuario sin reservas"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/users/v1/{user_without_bookings_id}/bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

@pytest.mark.asyncio
async def test_get_user_bookings_ordered(auth_token, user_id):
    """Test reservas ordenadas por fecha (más recientes primero)"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/users/v1/{user_id}/bookings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()

    # Verificar orden descendente por booking_date
    if len(data) > 1:
        for i in range(len(data) - 1):
            date1 = data[i]["booking"]["booking_date"]
            date2 = data[i + 1]["booking"]["booking_date"]
            assert date1 >= date2
```

---

## Paso 6: Documentación Mejorada

Agregar ejemplos en docstring:

```python
@router.get("/{user_id}/bookings", response_model=list[BookingWithTripResponse])
async def get_user_bookings(
    # ... parámetros ...
):
    """
    Listar todas las reservas de un usuario.

    ## Características
    - ✅ Incluye información completa del trayecto
    - ✅ Incluye información del conductor (nombre, email, teléfono)
    - ✅ Filtros por estado de reserva
    - ✅ Paginación
    - ✅ Ordenado por fecha de reserva (más recientes primero)

    ## Ejemplos de Uso

    **Todas las reservas:**
    ```
    GET /users/{id}/bookings
    ```

    **Solo confirmadas:**
    ```
    GET /users/{id}/bookings?status=confirmed
    ```

    **Solo canceladas:**
    ```
    GET /users/{id}/bookings?status=cancelled
    ```

    **Con paginación:**
    ```
    GET /users/{id}/bookings?skip=10&limit=5
    ```

    ## Estados de Reserva
    - `confirmed`: Reserva confirmada y activa
    - `cancelled`: Reserva cancelada por el usuario
    - `completed`: Viaje completado
    - `pending`: Pendiente de confirmación (futuro)

    ## Información Retornada
    Para cada reserva se incluye:
    - **booking**: Detalles de la reserva (id, fecha, plazas, estado)
    - **trip**: Información del trayecto (origen, destino, fecha/hora)
    - **driver**: Datos del conductor (nombre, email, teléfono, vehículo)
    """
    # ... código ...
```

---

## Paso 7: Importar UserResponse en trips schemas

**Archivo**: `apps/trips/api/versioning/v1/schemas/responses.py`

Agregar importación:

```python
from apps.users.api.versioning.v1.schemas.responses import UserResponse
```

---

## Checklist de Implementación

- [ ] Decidir ubicación del endpoint:
  - [ ] Opción 1: `GET /users/{id}/bookings` en users module
  - [ ] Opción 2: `GET /trips/my-bookings` en trips module
  - [ ] O implementar ambos
- [ ] Actualizar `BookingWithTripResponse` para incluir driver
- [ ] Mejorar método `get_by_passenger()` con filtro por estado
- [ ] Implementar endpoint con:
  - [ ] Validación de usuario autenticado
  - [ ] Validación de propiedad de reservas
  - [ ] Filtro por estado
  - [ ] Paginación
  - [ ] Enriquecimiento con datos de trip y driver
- [ ] Tests:
  - [ ] Obtener reservas propias
  - [ ] No puede ver reservas de otros
  - [ ] Filtro por estado
  - [ ] Paginación
  - [ ] Usuario sin reservas
  - [ ] Ordenación correcta
- [ ] Documentar en Swagger con ejemplos
- [ ] Verificar en /docs

---

## Verificación

```bash
# Obtener mis reservas (opción 2)
curl http://localhost:8000/api/v1/trips/v1/my-bookings \
  -H "Authorization: Bearer <TOKEN>"

# Obtener reservas de usuario específico (opción 1)
curl http://localhost:8000/api/v1/users/v1/<USER_ID>/bookings \
  -H "Authorization: Bearer <TOKEN>"

# Filtrar por estado
curl "http://localhost:8000/api/v1/users/v1/<USER_ID>/bookings?status=confirmed" \
  -H "Authorization: Bearer <TOKEN>"

# Con paginación
curl "http://localhost:8000/api/v1/users/v1/<USER_ID>/bookings?skip=0&limit=10" \
  -H "Authorization: Bearer <TOKEN>"

# Ver documentación
open http://localhost:8000/docs
```

---

## Criterios de Aceptación (de Issue #4)

✅ Usuario puede consultar todas sus reservas
✅ Lista incluye información completa de cada reserva
✅ Información del trayecto visible (origen, destino, fecha/hora)
✅ Datos del conductor accesibles (nombre, contacto)
✅ Filtros por estado de reserva
✅ Paginación implementada
✅ Ordenación por fecha (más recientes primero)
✅ Solo el usuario dueño puede ver sus reservas

---

## Próximo Paso

Una vez completado RF-004, proceder con:
- **RF-006**: Motor de Matching Avanzado (requisito complejo)
- **RF-005**: Visualización de Rutas en Mapa
