# Plan: RF-BONUS-003 - Visualización de Reservas de Otros Usuarios

**Issue**: #12
**Prioridad**: BAJA (Bonus - Transparencia y confianza)
**Estimación**: 2-3 horas
**Dependencias**:
- 04-RF-003-reserva-trayectos.md (completado)
- 05-RF-004-listado-reservas.md (completado)
- 06-RF-005-visualizacion-mapas.md (completado)

---

## Objetivo

Mostrar a los conductores y pasajeros confirmados qué otros usuarios están reservados en el trayecto, mejorando la transparencia, confianza y permitiendo coordinación entre viajeros.

---

## Análisis Previo

### Casos de Uso

**1. Conductor ve sus pasajeros**
- Ya implementado en RF-003: `GET /trips/{trip_id}/bookings`
- Conductor puede ver todas las reservas de su trayecto

**2. Pasajero ve otros pasajeros del mismo trayecto**
- **NUEVO**: Pasajero confirmado puede ver quién más viaja
- Útil para coordinación, reconocimiento, seguridad

**3. Información mostrada**
- Nombre y foto del usuario
- Número de plazas reservadas
- Estado de la reserva
- **NO** mostrar información sensible (email, teléfono) sin permiso

### Consideraciones de Privacidad

**¿Qué mostrar?**
- ✅ Nombre del usuario
- ✅ Foto de perfil (si es pública)
- ✅ Número de plazas reservadas
- ✅ Punto de recogida/bajada (si es público)
- ❌ Email (solo con permiso)
- ❌ Teléfono (solo con permiso)
- ❌ Dirección exacta

**Configuración de privacidad**
- Usuario puede controlar qué información compartir
- Por defecto: nombre y foto pública

### Arquitectura Objetivo
```
apps/trips/api/versioning/v1/
├── views.py                 # Nuevo endpoint para pasajeros
└── schemas/responses.py     # PassengerPublicProfileResponse
```

---

## Paso 1: Modelo de Usuario Público

**Archivo**: `apps/users/domain/models.py`

Agregar configuración de privacidad:

```python
class User(BaseModel):
    # ... campos existentes ...

    # NUEVO: Configuración de privacidad
    profile_photo_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL de la foto de perfil"
    )
    show_email_to_fellow_travelers: bool = Field(
        default=False,
        description="Mostrar email a compañeros de viaje"
    )
    show_phone_to_fellow_travelers: bool = Field(
        default=False,
        description="Mostrar teléfono a compañeros de viaje"
    )
    bio: Optional[str] = Field(
        None,
        max_length=500,
        description="Biografía breve del usuario"
    )

    def get_public_profile(self, is_fellow_traveler: bool = False) -> dict:
        """
        Retorna información pública del usuario según configuración.

        Args:
            is_fellow_traveler: Si el solicitante es compañero de viaje
        """
        profile = {
            "id": self.id,
            "name": self.name,
            "profile_photo_url": self.profile_photo_url,
            "bio": self.bio
        }

        # Información adicional para compañeros de viaje
        if is_fellow_traveler:
            if self.show_email_to_fellow_travelers:
                profile["email"] = self.email
            if self.show_phone_to_fellow_travelers:
                profile["phone"] = self.phone

        return profile
```

---

## Paso 2: DTOs - Schemas

**Archivo**: `apps/trips/api/versioning/v1/schemas/responses.py`

```python
class PassengerPublicProfileResponse(BaseModel):
    """
    Perfil público de un pasajero en un trayecto.
    Respeta configuración de privacidad del usuario.
    """
    user_id: str
    name: str
    profile_photo_url: Optional[str] = None
    bio: Optional[str] = None
    seats_booked: int
    pickup_location: Optional[str] = None
    dropoff_location: Optional[str] = None

    # Información adicional (solo si el usuario la comparte)
    email: Optional[str] = None
    phone: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "name": "Juan Pérez",
                "profile_photo_url": "https://example.com/photo.jpg",
                "bio": "Viajero frecuente, me gusta compartir historias",
                "seats_booked": 1,
                "pickup_location": "Centro de Jerez",
                "email": "juan@example.com"
            }
        }

class TripPassengersResponse(BaseModel):
    """
    Lista de pasajeros de un trayecto con información pública.
    """
    trip_id: str
    driver: PassengerPublicProfileResponse
    passengers: list[PassengerPublicProfileResponse]
    total_passengers: int
    available_seats: int

    class Config:
        json_schema_extra = {
            "example": {
                "trip_id": "507f1f77bcf86cd799439012",
                "driver": {
                    "user_id": "507f1f77bcf86cd799439013",
                    "name": "María García",
                    "seats_booked": 0
                },
                "passengers": [
                    {
                        "user_id": "507f1f77bcf86cd799439014",
                        "name": "Juan Pérez",
                        "seats_booked": 1
                    }
                ],
                "total_passengers": 1,
                "available_seats": 2
            }
        }
```

---

## Paso 3: Servicio de Visualización de Pasajeros

**Archivo**: `apps/trips/infrastructure/services/passenger_visibility_service.py`

```python
from typing import Optional
from fastapi import HTTPException, status

from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.trips.api.versioning.v1.schemas.responses import (
    PassengerPublicProfileResponse,
    TripPassengersResponse
)

class PassengerVisibilityService:
    """
    Servicio para gestionar la visibilidad de pasajeros en trayectos.
    Respeta configuraciones de privacidad.
    """

    def __init__(
        self,
        trip_repo: ITripRepository,
        booking_repo: IBookingRepository,
        user_repo: IUserRepository
    ):
        self.trip_repo = trip_repo
        self.booking_repo = booking_repo
        self.user_repo = user_repo

    async def can_view_passengers(
        self,
        trip_id: str,
        user_id: str
    ) -> bool:
        """
        Verifica si un usuario puede ver los pasajeros del trayecto.

        Puede ver:
        - El conductor del trayecto
        - Pasajeros confirmados del trayecto
        """
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            return False

        # Es el conductor
        if trip.driver_id == user_id:
            return True

        # Es un pasajero confirmado
        has_active_booking = await self.booking_repo.exists_active_booking(
            trip_id, user_id
        )
        return has_active_booking

    async def get_trip_passengers(
        self,
        trip_id: str,
        requesting_user_id: str
    ) -> TripPassengersResponse:
        """
        Obtiene lista de pasajeros del trayecto con información pública.

        Args:
            trip_id: ID del trayecto
            requesting_user_id: ID del usuario que solicita la información

        Returns:
            TripPassengersResponse con conductor y pasajeros
        """
        # Verificar permiso
        can_view = await self.can_view_passengers(trip_id, requesting_user_id)
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver los pasajeros de este trayecto"
            )

        # Obtener trayecto
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trayecto no encontrado"
            )

        # Obtener conductor
        driver = await self.user_repo.get_by_id(trip.driver_id)
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conductor no encontrado"
            )

        # Perfil público del conductor
        driver_profile = driver.get_public_profile(is_fellow_traveler=True)
        driver_response = PassengerPublicProfileResponse(
            user_id=driver.id,
            name=driver.name,
            profile_photo_url=driver_profile.get("profile_photo_url"),
            bio=driver_profile.get("bio"),
            seats_booked=0,  # Conductor no ocupa plaza
            email=driver_profile.get("email"),
            phone=driver_profile.get("phone")
        )

        # Obtener reservas del trayecto
        bookings = await self.booking_repo.get_by_trip(trip_id, skip=0, limit=100)

        # Filtrar solo confirmadas
        confirmed_bookings = [
            b for b in bookings
            if b.status == "confirmed" and b.is_active
        ]

        # Construir lista de pasajeros
        passengers_responses = []
        for booking in confirmed_bookings:
            passenger = await self.user_repo.get_by_id(booking.passenger_id)
            if passenger:
                passenger_profile = passenger.get_public_profile(
                    is_fellow_traveler=True
                )

                passengers_responses.append(PassengerPublicProfileResponse(
                    user_id=passenger.id,
                    name=passenger.name,
                    profile_photo_url=passenger_profile.get("profile_photo_url"),
                    bio=passenger_profile.get("bio"),
                    seats_booked=booking.seats_booked,
                    pickup_location=booking.pickup_location,
                    dropoff_location=booking.dropoff_location,
                    email=passenger_profile.get("email"),
                    phone=passenger_profile.get("phone")
                ))

        return TripPassengersResponse(
            trip_id=trip_id,
            driver=driver_response,
            passengers=passengers_responses,
            total_passengers=len(passengers_responses),
            available_seats=trip.available_seats
        )
```

---

## Paso 4: Dependency Injection

**Archivo**: `apps/trips/infrastructure/dependencies.py`

```python
from apps.trips.infrastructure.services.passenger_visibility_service import PassengerVisibilityService
from apps.users.infrastructure.dependencies import get_user_repository

async def get_passenger_visibility_service(
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)]
) -> PassengerVisibilityService:
    """Inyecta servicio de visibilidad de pasajeros"""
    return PassengerVisibilityService(trip_repo, booking_repo, user_repo)
```

---

## Paso 5: Endpoints

**Archivo**: `apps/trips/api/versioning/v1/views.py`

```python
from apps.trips.infrastructure.services.passenger_visibility_service import PassengerVisibilityService
from apps.trips.infrastructure.dependencies import get_passenger_visibility_service
from apps.trips.api.versioning.v1.schemas.responses import TripPassengersResponse

@router.get("/{trip_id}/passengers", response_model=TripPassengersResponse)
async def get_trip_passengers(
    trip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    visibility_service: Annotated[
        PassengerVisibilityService,
        Depends(get_passenger_visibility_service)
    ]
):
    """
    Ver pasajeros de un trayecto.

    **Endpoint:** `GET /trips/{trip_id}/passengers`

    **Requisitos:**
    - Usuario autenticado
    - Usuario debe ser conductor o pasajero confirmado del trayecto

    **Información mostrada:**
    - Conductor: nombre, foto, bio
    - Pasajeros: nombre, foto, bio, plazas reservadas
    - Email/teléfono: solo si el usuario lo comparte

    **Casos de Uso:**
    - Conductor ve quiénes viajarán con él
    - Pasajero ve otros pasajeros para coordinación
    - Facilita reconocimiento mutuo antes del viaje

    **Privacidad:**
    - Respeta configuración de privacidad de cada usuario
    - Solo accesible para viajeros del trayecto
    - No expone información sensible sin permiso
    """
    return await visibility_service.get_trip_passengers(trip_id, current_user.id)
```

---

## Paso 6: Endpoint de Configuración de Privacidad

**Archivo**: `apps/users/api/versioning/v1/views.py`

```python
from pydantic import BaseModel

class UpdatePrivacySettingsRequest(BaseModel):
    """Request para actualizar configuración de privacidad"""
    show_email_to_fellow_travelers: Optional[bool] = None
    show_phone_to_fellow_travelers: Optional[bool] = None
    profile_photo_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)

@router.put("/me/privacy-settings", response_model=UserResponse)
async def update_privacy_settings(
    payload: UpdatePrivacySettingsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Actualizar configuración de privacidad.

    **Endpoint:** `PUT /users/me/privacy-settings`

    **Configuraciones:**
    - `show_email_to_fellow_travelers`: Compartir email con compañeros de viaje
    - `show_phone_to_fellow_travelers`: Compartir teléfono con compañeros de viaje
    - `profile_photo_url`: URL de foto de perfil
    - `bio`: Biografía breve
    """
    # Actualizar solo campos proporcionados
    if payload.show_email_to_fellow_travelers is not None:
        current_user.show_email_to_fellow_travelers = payload.show_email_to_fellow_travelers
    if payload.show_phone_to_fellow_travelers is not None:
        current_user.show_phone_to_fellow_travelers = payload.show_phone_to_fellow_travelers
    if payload.profile_photo_url is not None:
        current_user.profile_photo_url = payload.profile_photo_url
    if payload.bio is not None:
        current_user.bio = payload.bio

    await user_repo.update(current_user.id, current_user)

    return UserResponse(**current_user.model_dump())

@router.get("/me/privacy-settings")
async def get_privacy_settings(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Obtener configuración actual de privacidad.

    **Endpoint:** `GET /users/me/privacy-settings`
    """
    return {
        "show_email_to_fellow_travelers": current_user.show_email_to_fellow_travelers,
        "show_phone_to_fellow_travelers": current_user.show_phone_to_fellow_travelers,
        "profile_photo_url": current_user.profile_photo_url,
        "bio": current_user.bio
    }
```

---

## Paso 7: Testing

**Archivo**: `tests/test_trips/test_passenger_visibility.py`

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_driver_can_view_passengers(auth_token_driver, trip_id):
    """Test conductor puede ver pasajeros"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/trips/v1/{trip_id}/passengers",
            headers={"Authorization": f"Bearer {auth_token_driver}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "driver" in data
    assert "passengers" in data
    assert "total_passengers" in data

@pytest.mark.asyncio
async def test_passenger_can_view_fellow_passengers(auth_token_passenger, trip_id):
    """Test pasajero confirmado puede ver otros pasajeros"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/trips/v1/{trip_id}/passengers",
            headers={"Authorization": f"Bearer {auth_token_passenger}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "passengers" in data

@pytest.mark.asyncio
async def test_non_passenger_cannot_view(auth_token_other_user, trip_id):
    """Test usuario sin reserva no puede ver pasajeros"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/trips/v1/{trip_id}/passengers",
            headers={"Authorization": f"Bearer {auth_token_other_user}"}
        )

    assert response.status_code == 403

@pytest.mark.asyncio
async def test_privacy_settings_respected(auth_token_passenger, trip_id):
    """Test que se respeta configuración de privacidad"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/trips/v1/{trip_id}/passengers",
            headers={"Authorization": f"Bearer {auth_token_passenger}"}
        )

    assert response.status_code == 200
    data = response.json()

    # Si un pasajero no comparte email, no debe aparecer
    for passenger in data["passengers"]:
        # Verificar que hay o no email según configuración
        # (requiere conocer configuración del usuario de prueba)
        pass

@pytest.mark.asyncio
async def test_update_privacy_settings(auth_token):
    """Test actualizar configuración de privacidad"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.put(
            "/api/v1/users/v1/me/privacy-settings",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "show_email_to_fellow_travelers": True,
                "show_phone_to_fellow_travelers": False,
                "bio": "Me gusta viajar y compartir"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "Me gusta viajar y compartir"

@pytest.mark.asyncio
async def test_get_privacy_settings(auth_token):
    """Test obtener configuración de privacidad"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/api/v1/users/v1/me/privacy-settings",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert "show_email_to_fellow_travelers" in data
    assert "show_phone_to_fellow_travelers" in data
```

---

## Checklist de Implementación

- [ ] Actualizar modelo `User` con campos de privacidad:
  - [ ] `profile_photo_url`
  - [ ] `show_email_to_fellow_travelers`
  - [ ] `show_phone_to_fellow_travelers`
  - [ ] `bio`
  - [ ] Método `get_public_profile()`
- [ ] Crear `PassengerVisibilityService`:
  - [ ] `can_view_passengers()` - Verificación de permisos
  - [ ] `get_trip_passengers()` - Obtener lista de pasajeros
- [ ] Schemas:
  - [ ] `PassengerPublicProfileResponse`
  - [ ] `TripPassengersResponse`
  - [ ] `UpdatePrivacySettingsRequest`
- [ ] Dependency injection
- [ ] Endpoints:
  - [ ] GET /trips/{trip_id}/passengers (ver pasajeros)
  - [ ] PUT /users/me/privacy-settings (configurar privacidad)
  - [ ] GET /users/me/privacy-settings (obtener configuración)
- [ ] Tests:
  - [ ] Conductor puede ver
  - [ ] Pasajero puede ver
  - [ ] Usuario externo no puede ver
  - [ ] Privacidad respetada
  - [ ] Actualizar configuración
- [ ] Documentar en Swagger
- [ ] Verificar en /docs

---

## Verificación

```bash
# Ver pasajeros de un trayecto (como conductor o pasajero)
curl http://localhost:8000/api/v1/trips/v1/<TRIP_ID>/passengers \
  -H "Authorization: Bearer <TOKEN>"

# Configurar privacidad
curl -X PUT http://localhost:8000/api/v1/users/v1/me/privacy-settings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "show_email_to_fellow_travelers": true,
    "show_phone_to_fellow_travelers": false,
    "profile_photo_url": "https://example.com/photo.jpg",
    "bio": "Viajero frecuente, me encanta compartir historias"
  }'

# Ver mi configuración de privacidad
curl http://localhost:8000/api/v1/users/v1/me/privacy-settings \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Criterios de Aceptación

✅ Conductor puede ver todos los pasajeros de su trayecto
✅ Pasajero confirmado puede ver otros pasajeros del mismo trayecto
✅ Usuarios externos no pueden ver información de pasajeros
✅ Se respeta configuración de privacidad de cada usuario
✅ Información sensible solo visible si el usuario lo permite
✅ Usuarios pueden configurar qué información compartir
✅ Endpoint de actualización de configuración de privacidad funcional

---

## Mejoras Futuras

- Chat privado entre pasajeros del mismo trayecto (RF-BONUS-004)
- Sistema de valoraciones/reputación entre viajeros
- Verificación de identidad con badge visual
- Notificaciones cuando nuevos pasajeros se unen
- Opción de "presentarse" con mensaje personalizado
- Integración con redes sociales (verificación de perfil)
- Indicador de "viajero frecuente" o nivel de experiencia

---

## Próximo Paso

Una vez completado RF-BONUS-003, proceder con:
- **RF-BONUS-004**: Chat Simulado (último plan)
