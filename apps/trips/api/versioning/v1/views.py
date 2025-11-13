"""FastAPI endpoints for trips management."""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import date as dt_date

from apps.trips.domain.models import Trip, TripStatus
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.services.co2_service import ICO2Service
from apps.trips.infrastructure.dependencies import get_trip_repository, get_booking_repository, get_booking_service, get_co2_service
from apps.trips.infrastructure.services.booking_service import BookingService
from apps.trips.api.versioning.v1.schemas.requests import CreateTripRequest, UpdateTripRequest, BookTripRequest
from apps.trips.api.versioning.v1.schemas.responses import (
    TripResponse,
    TripListResponse,
    BookingResponse,
    BookingWithTripResponse,
    BookingListResponse,
    CO2ImpactResponse,
    UserCO2StatsResponse
)

# Import authentication from users
from apps.users.infrastructure.dependencies import get_current_user, get_current_active_user, get_user_repository
from apps.users.domain.models import User, UserRole
from apps.users.domain.repositories.user_repository import IUserRepository
from apps.users.api.versioning.v1.schemas.responses import UserResponse
from shared.exceptions import Forbidden, EntityNotFound, ValidationError

router = APIRouter()


@router.post("/", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    payload: CreateTripRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    co2_service: Annotated[ICO2Service, Depends(get_co2_service)]
):
    """
    Publicar nuevo trayecto.

    **Requisitos:**
    - Usuario autenticado y activo
    - Usuario debe tener rol de conductor (driver o both)
    - Todos los campos requeridos presentes
    - Fecha debe ser futura

    **Reglas de Negocio:**
    - available_seats >= 1
    - departure_date >= hoy
    """
    # Validar rol de conductor
    if not current_user.is_driver():
        raise Forbidden("Solo los conductores pueden publicar trayectos")

    # Validar fecha futura
    if payload.departure_date < dt_date.today():
        raise ValidationError("La fecha del trayecto debe ser futura")

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
        estimated_arrival_time=payload.estimated_arrival_time,
        origin_lat=payload.origin_lat,
        origin_lng=payload.origin_lng,
        destination_lat=payload.destination_lat,
        destination_lng=payload.destination_lng,
        vehicle_type=payload.vehicle_type,  # RF-BONUS-002
        status=TripStatus.ACTIVE
    )

    # Calculate CO₂ impact (RF-BONUS-002)
    if trip.origin_lat and trip.origin_lng and trip.destination_lat and trip.destination_lng:
        trip = await co2_service.calculate_and_update_co2(trip)

    # Guardar en BD
    created_trip = await repo.create(trip)

    return TripResponse.model_validate(created_trip)


@router.get("/search", response_model=TripListResponse)
async def search_trips(
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    origin: Optional[str] = Query(None, description="Ciudad de origen (búsqueda aproximada, case-insensitive)"),
    destination: Optional[str] = Query(None, description="Ciudad de destino (búsqueda aproximada, case-insensitive)"),
    date_from: Optional[dt_date] = Query(None, description="Fecha mínima (YYYY-MM-DD). Por defecto: hoy"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros")
):
    """
    Buscar trayectos disponibles con filtros (RF-002).

    ## Características
    - ✅ Búsqueda **aproximada** por ciudad (case-insensitive, parcial)
    - ✅ Filtro por fecha (por defecto, solo trayectos futuros)
    - ✅ Solo retorna trayectos activos con plazas disponibles
    - ✅ Ordenados por fecha de salida (más cercanos primero)
    - ✅ No requiere autenticación (búsqueda pública)

    ## Ejemplos de Uso

    **Búsqueda exacta:**
    ```
    GET /trips/search?origin=Cádiz&destination=Sevilla
    ```

    **Búsqueda aproximada (case-insensitive):**
    ```
    GET /trips/search?origin=cadiz&destination=sev
    ```
    Retorna trayectos donde origen contiene "cadiz" y destino contiene "sev"

    **Filtro por fecha:**
    ```
    GET /trips/search?date_from=2025-12-15
    ```

    **Solo origen:**
    ```
    GET /trips/search?origin=Cádiz
    ```

    **Paginación:**
    ```
    GET /trips/search?origin=Cádiz&skip=10&limit=5
    ```

    ## Reglas de Negocio
    - Solo trayectos con `status = "active"`
    - Solo trayectos con `available_seats > 0`
    - Solo trayectos con `is_active = True`
    - Por defecto, solo trayectos con `departure_date >= hoy`
    """
    # Buscar trayectos usando el repositorio
    trips = await repo.search(
        origin=origin,
        destination=destination,
        date_from=date_from,
        skip=skip,
        limit=limit
    )

    # El repositorio ya filtra por plazas disponibles
    return TripListResponse(
        trips=[TripResponse.model_validate(t) for t in trips],
        total=len(trips),  # TODO: Agregar count en repositorio para total real
        skip=skip,
        limit=limit
    )


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: int,
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Obtener trayecto por ID.

    - No requiere autenticación (búsqueda pública)
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    return TripResponse.model_validate(trip)


@router.get("/", response_model=TripListResponse)
async def list_trips(
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    status: Optional[str] = Query(None, description="Filtrar por estado (active, completed, cancelled)")
):
    """
    Listar todos los trayectos con paginación.

    - No requiere autenticación
    - Soporta filtro por estado
    """
    trips = await repo.get_all(skip=skip, limit=limit, status=status)
    total = await repo.count_active() if status == "active" or status is None else len(trips)

    return TripListResponse(
        trips=[TripResponse.model_validate(t) for t in trips],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/driver/{driver_id}", response_model=TripListResponse)
async def list_trips_by_driver(
    driver_id: int,
    repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Listar trayectos de un conductor específico.

    - No requiere autenticación (perfil público)
    """
    trips = await repo.get_by_driver(driver_id, skip=skip, limit=limit)

    return TripListResponse(
        trips=[TripResponse.model_validate(t) for t in trips],
        total=len(trips),
        skip=skip,
        limit=limit
    )


@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
    trip_id: int,
    payload: UpdateTripRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Actualizar trayecto existente.

    **Requisitos:**
    - Usuario autenticado y activo
    - Solo el conductor propietario puede actualizar

    **Actualización parcial:** Solo se actualizan los campos proporcionados.
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    # Verificar propiedad
    if trip.driver_id != current_user.id:
        raise Forbidden("Solo el conductor propietario puede actualizar el trayecto")

    # Actualizar solo campos proporcionados (partial update)
    if payload.available_seats is not None:
        trip.available_seats = payload.available_seats
    if payload.price_per_seat is not None:
        trip.price_per_seat = payload.price_per_seat
    if payload.description is not None:
        trip.description = payload.description
    if payload.status is not None:
        trip.status = TripStatus(payload.status)
    if payload.max_detour_minutes is not None:
        trip.max_detour_minutes = payload.max_detour_minutes

    success = await repo.update(trip_id, trip)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar trayecto"
        )

    # Re-fetch updated trip
    updated_trip = await repo.get_by_id(trip_id)
    return TripResponse.model_validate(updated_trip)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Eliminar (cancelar) trayecto.

    **Requisitos:**
    - Usuario autenticado y activo
    - Solo el conductor propietario puede eliminar

    **Soft delete:** El trayecto se marca como is_active=False y status=cancelled
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    # Verificar propiedad
    if trip.driver_id != current_user.id:
        raise Forbidden("Solo el conductor propietario puede eliminar el trayecto")

    success = await repo.delete(trip_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar trayecto"
        )

    return None


# ============= BOOKING ENDPOINTS =============


@router.get("/bookings/my", response_model=list[BookingWithTripResponse])
async def list_my_bookings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)],
    status: Optional[str] = Query(None, description="Filtrar por estado (confirmed, cancelled, completed)"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros")
):
    """
    Listar mis reservas (RF-004).

    **Características:**
    - Lista todas las reservas del usuario autenticado
    - Incluye información completa del trayecto y conductor
    - Soporta filtro por estado
    - Soporta paginación
    - Ordenadas por fecha de reserva (más recientes primero)

    **Requisitos:**
    - Usuario autenticado

    **Ejemplo de uso:**
    ```
    GET /trips/bookings/my
    GET /trips/bookings/my?status=confirmed
    GET /trips/bookings/my?skip=10&limit=5
    ```
    """
    # Obtener reservas del usuario
    bookings = await booking_repo.get_by_passenger(
        current_user.id,
        skip=skip,
        limit=limit
    )

    # Filtrar por estado si se especifica
    if status:
        bookings = [b for b in bookings if b.status == status]

    # Enriquecer con información de trayectos y conductores
    enriched_bookings = []
    for booking in bookings:
        # Obtener trayecto
        trip = await trip_repo.get_by_id(booking.trip_id)
        if not trip:
            continue  # Skip if trip no longer exists

        # Obtener conductor
        driver = await user_repo.get_by_id(trip.driver_id)

        enriched_bookings.append(
            BookingWithTripResponse(
                booking=BookingResponse.model_validate(booking),
                trip=TripResponse.model_validate(trip),
                driver=UserResponse.model_validate(driver) if driver else None
            )
        )

    return enriched_bookings


@router.post("/{trip_id}/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def book_trip(
    trip_id: int,
    payload: BookTripRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)]
):
    """
    Reservar plaza en un trayecto (RF-003).

    **Endpoint:** `POST /trips/{trip_id}/book`

    **Requisitos:**
    - Usuario autenticado y activo
    - Trayecto debe existir y estar activo
    - Debe haber plazas disponibles
    - Usuario no puede ser el conductor
    - No puede tener reserva duplicada

    **Proceso:**
    1. Valida disponibilidad (RF-INF-002)
    2. Crea la reserva
    3. Decrementa plazas disponibles (RF-INF-004)

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
        passenger_notes=payload.passenger_notes,
        pickup_location=payload.pickup_location,
        dropoff_location=payload.dropoff_location
    )

    return BookingResponse.model_validate(created_booking)


@router.get("/bookings/{booking_id}", response_model=BookingWithTripResponse)
async def get_booking(
    booking_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    booking_service: Annotated[BookingService, Depends(get_booking_service)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    user_repo: Annotated[IUserRepository, Depends(get_user_repository)]
):
    """
    Obtener detalles de una reserva con información del trayecto y conductor.

    **Requisitos:**
    - Usuario autenticado
    - Solo el pasajero o el conductor pueden ver la reserva
    """
    booking, is_driver = await booking_service.get_booking_with_validation(
        booking_id, current_user.id
    )

    # Obtener trayecto asociado
    trip = await trip_repo.get_by_id(booking.trip_id)
    if not trip:
        raise EntityNotFound("Trip", booking.trip_id)

    # Obtener información del conductor
    driver = await user_repo.get_by_id(trip.driver_id)

    return BookingWithTripResponse(
        booking=BookingResponse.model_validate(booking),
        trip=TripResponse.model_validate(trip),
        driver=UserResponse.model_validate(driver) if driver else None
    )


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    booking_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
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
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
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
        raise EntityNotFound("Trip", trip_id)

    # Verificar que el usuario es el conductor
    if trip.driver_id != current_user.id:
        raise Forbidden("Solo el conductor puede ver las reservas del trayecto")

    bookings = await booking_repo.get_by_trip(trip_id, skip=skip, limit=limit)

    return BookingListResponse(
        bookings=[BookingResponse.model_validate(b) for b in bookings],
        total=len(bookings),
        skip=skip,
        limit=limit
    )
