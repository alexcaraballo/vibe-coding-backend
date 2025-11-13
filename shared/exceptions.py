"""Domain exceptions for the carpooling system."""


class DomainException(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class EntityNotFound(DomainException):
    """Raised when a requested entity cannot be found."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="ENTITY_NOT_FOUND"
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class ValidationError(DomainException):
    """Raised when business validation rules are violated."""

    def __init__(self, message: str):
        super().__init__(message=message, code="VALIDATION_ERROR")


class InsufficientSeats(DomainException):
    """Raised when trying to book a trip with no available seats."""

    def __init__(self):
        super().__init__(
            message="No hay plazas disponibles en este trayecto",
            code="INSUFFICIENT_SEATS"
        )


class MaxDetourExceeded(DomainException):
    """Raised when a booking would exceed the maximum allowed detour time."""

    def __init__(self, current: int, additional: int, max_allowed: int):
        super().__init__(
            message=f"Desvío excedido: {current + additional} > {max_allowed} minutos",
            code="MAX_DETOUR_EXCEEDED"
        )
        self.current_detour = current
        self.additional_detour = additional
        self.max_allowed = max_allowed


class DuplicateEntity(DomainException):
    """Raised when trying to create an entity that already exists."""

    def __init__(self, entity_type: str, field: str, value: str):
        super().__init__(
            message=f"{entity_type} with {field} '{value}' already exists",
            code="DUPLICATE_ENTITY"
        )
        self.entity_type = entity_type
        self.field = field
        self.value = value


class Unauthorized(DomainException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message=message, code="UNAUTHORIZED")


class Forbidden(DomainException):
    """Raised when user lacks permission for an operation."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, code="FORBIDDEN")


class BookingAlreadyExists(DomainException):
    """Raised when user tries to book the same trip twice."""

    def __init__(self):
        super().__init__(
            message="Ya tienes una reserva activa para este trayecto",
            code="BOOKING_ALREADY_EXISTS"
        )


class TripAlreadyStarted(DomainException):
    """Raised when trying to modify or cancel a trip that has already started."""

    def __init__(self):
        super().__init__(
            message="No se puede modificar o cancelar un trayecto que ya ha comenzado",
            code="TRIP_ALREADY_STARTED"
        )


class InvalidOperation(DomainException):
    """Raised when an operation is not valid in the current state."""

    def __init__(self, message: str):
        super().__init__(message=message, code="INVALID_OPERATION")
