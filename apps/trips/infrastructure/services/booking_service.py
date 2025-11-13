"""Booking service with business logic."""
from typing import Optional

from apps.trips.domain.models import Booking, TripStatus
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from shared.exceptions import (
    InsufficientSeats,
    ValidationError,
    EntityNotFound,
    Forbidden,
    BookingAlreadyExists
)


class BookingService:
    """
    Servicio de lógica de negocio para reservas.
    Implementa:
    - RF-INF-002: Validación de disponibilidad
    - RF-INF-004: Gestión de plazas
    - RF-INF-003: Cancelación de reservas
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
        trip_id: int,
        passenger_id: int,
        seats_requested: int = 1,
        passenger_notes: Optional[str] = None,
        pickup_location: Optional[str] = None,
        dropoff_location: Optional[str] = None,
        pickup_lat: Optional[float] = None,
        pickup_lng: Optional[float] = None,
        dropoff_lat: Optional[float] = None,
        dropoff_lng: Optional[float] = None
    ) -> Booking:
        """
        Crea una reserva con validaciones completas.

        RF-INF-002: Validación de Disponibilidad
        RF-INF-004: Gestión de Plazas

        Raises:
            EntityNotFound: Si el trayecto no existe
            ValidationError: Si las validaciones de negocio fallan
            InsufficientSeats: Si no hay plazas disponibles
            BookingAlreadyExists: Si ya existe una reserva activa
        """
        # 1. Validar que el trayecto existe
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise EntityNotFound("Trip", trip_id)

        # 2. Validar que el trayecto está activo
        if trip.status != TripStatus.ACTIVE or not trip.is_active:
            raise ValidationError("El trayecto no está disponible")

        # 3. RF-INF-002: Validar disponibilidad de plazas
        if not trip.can_accommodate(seats_requested):
            raise InsufficientSeats()

        # 4. Validar que el pasajero no es el conductor
        if trip.driver_id == passenger_id:
            raise ValidationError("El conductor no puede reservar su propio trayecto")

        # 5. Validar que no hay reserva duplicada
        has_booking = await self.booking_repo.exists_active_booking(trip_id, passenger_id)
        if has_booking:
            raise BookingAlreadyExists()

        # 6. Validar número de plazas solicitadas
        if seats_requested < 1 or seats_requested > trip.available_seats:
            raise ValidationError(
                f"Número de plazas inválido. Disponibles: {trip.available_seats}"
            )

        # 7. Crear la reserva
        booking = Booking(
            trip_id=trip_id,
            passenger_id=passenger_id,
            seats_booked=seats_requested,
            passenger_notes=passenger_notes,
            pickup_location=pickup_location,
            dropoff_location=dropoff_location,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng
        )

        created_booking = await self.booking_repo.create(booking)

        # 8. RF-INF-004: Actualizar plazas disponibles del trayecto
        trip.reserve_seats(seats_requested)
        await self.trip_repo.update(trip_id, trip)

        return created_booking

    async def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        """
        Cancela una reserva y libera las plazas (RF-INF-003).

        RF-INF-004: Gestión de Plazas (incrementar al cancelar)

        Raises:
            EntityNotFound: Si la reserva no existe
            Forbidden: Si el usuario no es el dueño
            ValidationError: Si la reserva no puede ser cancelada
        """
        # 1. Obtener la reserva
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise EntityNotFound("Booking", booking_id)

        # 2. Validar que el usuario es el dueño de la reserva
        if booking.passenger_id != user_id:
            raise Forbidden("No puedes cancelar reservas de otros usuarios")

        # 3. Validar que la reserva puede ser cancelada
        if not booking.can_be_cancelled():
            raise ValidationError("Esta reserva no puede ser cancelada")

        # 4. Obtener el trayecto
        trip = await self.trip_repo.get_by_id(booking.trip_id)
        if not trip:
            raise EntityNotFound("Trip", booking.trip_id)

        # 5. Cancelar la reserva
        booking.cancel()
        await self.booking_repo.update(booking_id, booking)

        # 6. RF-INF-004: Liberar plazas
        trip.release_seats(booking.seats_booked)
        await self.trip_repo.update(booking.trip_id, trip)

        return True

    async def get_booking_with_validation(
        self,
        booking_id: int,
        user_id: int
    ) -> tuple[Booking, bool]:
        """
        Get booking with access validation.

        Returns:
            tuple[Booking, bool]: (booking, is_driver)

        Raises:
            EntityNotFound: If booking not found
        """
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise EntityNotFound("Booking", booking_id)

        trip = await self.trip_repo.get_by_id(booking.trip_id)
        if not trip:
            raise EntityNotFound("Trip", booking.trip_id)

        # Check if user is passenger or driver
        is_driver = trip.driver_id == user_id
        is_passenger = booking.passenger_id == user_id

        if not (is_driver or is_passenger):
            raise Forbidden("No tienes permiso para ver esta reserva")

        return booking, is_driver
