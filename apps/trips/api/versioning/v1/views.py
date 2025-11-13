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
    UserCO2StatsResponse,
    TripWithBookingsVisualizationResponse,
    PublicBookingLocationResponse,
    TripRouteWithStopsResponse,
    WaypointResponse
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
        dropoff_location=payload.dropoff_location,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        dropoff_lat=payload.dropoff_lat,
        dropoff_lng=payload.dropoff_lng
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


@router.get("/{trip_id}/co2-impact", response_model=CO2ImpactResponse)
async def get_trip_co2_impact(
    trip_id: int,
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    co2_service: Annotated[ICO2Service, Depends(get_co2_service)]
):
    """
    Obtener impacto de CO₂ de un trayecto específico (RF-BONUS-002).

    **Endpoint:** `GET /trips/{trip_id}/co2-impact`

    **Características:**
    - Muestra el CO₂ evitado por el trayecto
    - Calcula el CO₂ si no está calculado aún
    - Muestra equivalencias (árboles plantados, km no conducidos)
    - No requiere autenticación (información pública)

    **Ejemplo de uso:**
    ```
    GET /api/v1/trips/123/co2-impact
    ```

    **Respuesta:**
    - vehicle_type: Tipo de vehículo
    - distance_km: Distancia del trayecto
    - co2_saved_per_passenger_kg: CO₂ evitado por pasajero
    - total_co2_saved_kg: CO₂ total evitado
    - passengers_count: Número de pasajeros que han reservado
    - equivalences: Equivalencias para entender el impacto
    """
    # Get trip
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    # Calculate CO₂ if not calculated yet
    if not trip.co2_saved_per_passenger_kg:
        trip = await co2_service.calculate_and_update_co2(trip)
        await trip_repo.update(trip_id, trip)

    # Calculate passengers count
    passengers_count = trip.total_seats - trip.available_seats

    # Calculate equivalences
    total_co2 = trip.total_co2_saved_kg or 0.0
    equivalence_trees = round(total_co2 * 0.4, 1)
    equivalence_km = round(total_co2 * 5.0, 1)

    return CO2ImpactResponse(
        trip_id=trip.id,
        vehicle_type=trip.vehicle_type.value,
        distance_km=trip.distance_km,
        co2_saved_per_passenger_kg=trip.co2_saved_per_passenger_kg,
        total_co2_saved_kg=trip.total_co2_saved_kg,
        passengers_count=passengers_count,
        equivalences={
            "trees": f"Equivalente a plantar {equivalence_trees} árboles por un año",
            "km": f"Equivalente a no conducir {equivalence_km} km en coche convencional"
        }
    )


@router.get("/users/me/co2-stats", response_model=UserCO2StatsResponse)
async def get_my_co2_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    co2_service: Annotated[ICO2Service, Depends(get_co2_service)]
):
    """
    Obtener estadísticas de CO₂ del usuario autenticado (RF-BONUS-002).

    **Endpoint:** `GET /trips/users/me/co2-stats`

    **Características:**
    - Muestra el CO₂ total evitado por el usuario
    - Incluye viajes como conductor y como pasajero
    - Calcula equivalencias motivacionales
    - Requiere autenticación

    **Estadísticas incluidas:**
    - total_co2_saved_kg: Total de CO₂ evitado
    - trips_as_driver: Número de viajes como conductor
    - trips_as_passenger: Número de viajes como pasajero
    - total_trips: Total de viajes
    - average_co2_per_trip_kg: Promedio de CO₂ por viaje
    - equivalence_trees: Árboles plantados equivalente
    - equivalence_km_not_driven: Kilómetros no conducidos equivalente

    **Ejemplo de uso:**
    ```
    GET /api/v1/trips/users/me/co2-stats
    Authorization: Bearer <token>
    ```
    """
    stats = await co2_service.get_user_co2_stats(current_user.id)
    return UserCO2StatsResponse(**stats)


@router.get("/{trip_id}/bookings/public", response_model=TripWithBookingsVisualizationResponse)
async def get_trip_bookings_public(
    trip_id: int,
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)]
):
    """
    Obtener visualización pública de reservas de un trayecto (RF-BONUS-003).

    **Endpoint:** `GET /trips/{trip_id}/bookings/public`

    **Características:**
    - Muestra información pública de las reservas (sin datos personales)
    - Incluye puntos de recogida y bajada con coordenadas
    - Útil para visualizar en mapa las paradas del trayecto
    - No requiere autenticación (información pública)
    - Protege privacidad: no expone nombres ni IDs de pasajeros

    **Información expuesta:**
    - Número de plazas reservadas por cada reserva
    - Ubicaciones de recogida y bajada (si están definidas)
    - Coordenadas geográficas de las ubicaciones
    - Fecha de reserva
    - Total de reservas y plazas reservadas

    **Información NO expuesta (privada):**
    - Nombres de pasajeros
    - IDs de pasajeros
    - Notas de pasajeros
    - Información de contacto

    **Ejemplo de uso:**
    ```
    GET /api/v1/trips/123/bookings/public
    ```

    **Caso de uso:**
    Permite a cualquier usuario (incluyendo no autenticados) ver las paradas
    intermedias de un trayecto en un mapa, ayudando a decidir si el trayecto
    les conviene según las ubicaciones de recogida/bajada.
    """
    # Get trip
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    # Get all active bookings for this trip
    bookings = await booking_repo.get_by_trip(trip_id, skip=0, limit=1000)

    # Filter only confirmed bookings
    active_bookings = [b for b in bookings if b.status == "confirmed" and b.is_active]

    # Create public booking responses (anonymized)
    public_bookings = []
    total_seats_booked = 0

    for booking in active_bookings:
        total_seats_booked += booking.seats_booked

        # Only include bookings with location information
        if booking.pickup_location or booking.dropoff_location:
            public_bookings.append(
                PublicBookingLocationResponse(
                    booking_id=booking.id,
                    seats_booked=booking.seats_booked,
                    pickup_location=booking.pickup_location,
                    dropoff_location=booking.dropoff_location,
                    pickup_lat=booking.pickup_lat if hasattr(booking, 'pickup_lat') else None,
                    pickup_lng=booking.pickup_lng if hasattr(booking, 'pickup_lng') else None,
                    dropoff_lat=booking.dropoff_lat if hasattr(booking, 'dropoff_lat') else None,
                    dropoff_lng=booking.dropoff_lng if hasattr(booking, 'dropoff_lng') else None,
                    booking_date=booking.booking_date
                )
            )

    return TripWithBookingsVisualizationResponse(
        trip=TripResponse.model_validate(trip),
        total_bookings=len(active_bookings),
        total_seats_booked=total_seats_booked,
        bookings=public_bookings
    )


@router.get("/{trip_id}/route-with-stops", response_model=TripRouteWithStopsResponse)
async def get_trip_route_with_stops(
    trip_id: int,
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)]
):
    """
    Obtener ruta completa del trayecto con todas las paradas para visualización en mapa (RF-BONUS-003).

    **Endpoint:** `GET /trips/{trip_id}/route-with-stops`

    **Características:**
    - Devuelve origen, destino y todos los puntos intermedios (recogidas/bajadas)
    - Waypoints ordenados para visualización en mapa
    - Incluye coordenadas geográficas para cada punto
    - No requiere autenticación (información pública)
    - Útil para dibujar ruta completa en mapa interactivo

    **Tipos de waypoints:**
    - `origin`: Punto de origen del trayecto
    - `destination`: Punto de destino del trayecto
    - `pickup`: Punto de recogida de pasajero
    - `dropoff`: Punto de bajada de pasajero

    **Ejemplo de uso:**
    ```
    GET /api/v1/trips/123/route-with-stops
    ```

    **Respuesta:**
    Lista ordenada de waypoints desde el origen hasta el destino,
    incluyendo todas las paradas intermedias de recogida y bajada.

    **Caso de uso:**
    Permite visualizar en un mapa la ruta completa con todas las paradas,
    mostrando a potenciales pasajeros el recorrido exacto que hará el conductor.
    """
    # Get trip
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise EntityNotFound("Trip", trip_id)

    # Get all active bookings with confirmed status
    bookings = await booking_repo.get_by_trip(trip_id, skip=0, limit=1000)
    active_bookings = [b for b in bookings if b.status == "confirmed" and b.is_active]

    # Build waypoints list
    waypoints = []
    order = 0

    # 1. Add origin
    if trip.origin_lat and trip.origin_lng:
        waypoints.append(
            WaypointResponse(
                type="origin",
                location=trip.origin,
                lat=trip.origin_lat,
                lng=trip.origin_lng,
                booking_id=None,
                order=order
            )
        )
        order += 1

    # 2. Add pickup points from bookings
    for booking in active_bookings:
        if booking.pickup_location and hasattr(booking, 'pickup_lat') and booking.pickup_lat:
            waypoints.append(
                WaypointResponse(
                    type="pickup",
                    location=booking.pickup_location,
                    lat=booking.pickup_lat,
                    lng=booking.pickup_lng,
                    booking_id=booking.id,
                    order=order
                )
            )
            order += 1

    # 3. Add dropoff points from bookings
    for booking in active_bookings:
        if booking.dropoff_location and hasattr(booking, 'dropoff_lat') and booking.dropoff_lat:
            waypoints.append(
                WaypointResponse(
                    type="dropoff",
                    location=booking.dropoff_location,
                    lat=booking.dropoff_lat,
                    lng=booking.dropoff_lng,
                    booking_id=booking.id,
                    order=order
                )
            )
            order += 1

    # 4. Add destination
    if trip.destination_lat and trip.destination_lng:
        waypoints.append(
            WaypointResponse(
                type="destination",
                location=trip.destination,
                lat=trip.destination_lat,
                lng=trip.destination_lng,
                booking_id=None,
                order=order
            )
        )

    return TripRouteWithStopsResponse(
        trip_id=trip.id,
        origin=trip.origin,
        destination=trip.destination,
        waypoints=waypoints,
        total_distance_km=trip.distance_km,
        estimated_duration_minutes=None  # TODO: Calculate based on distance and speed
    )
