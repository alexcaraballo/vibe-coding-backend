"""FastAPI endpoints for chat management (RF-BONUS-004)."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query

from apps.trips.domain.models import ChatMessage
from apps.trips.domain.repositories.chat_repository import IChatRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.infrastructure.dependencies import (
    get_chat_repository,
    get_booking_repository,
    get_trip_repository
)
from apps.trips.api.versioning.v1.schemas.requests import SendChatMessageRequest
from apps.trips.api.versioning.v1.schemas.responses import (
    ChatMessageResponse,
    ChatConversationResponse
)

# Import authentication from users
from apps.users.infrastructure.dependencies import get_current_active_user
from apps.users.domain.models import User
from shared.exceptions import Forbidden, EntityNotFound, ValidationError

router = APIRouter()


@router.post("/bookings/{booking_id}/chat", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    booking_id: int,
    payload: SendChatMessageRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    chat_repo: Annotated[IChatRepository, Depends(get_chat_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)]
):
    """
    Enviar mensaje de chat en una reserva (RF-BONUS-004).

    **Endpoint:** `POST /trips/bookings/{booking_id}/chat`

    **Requisitos:**
    - Usuario autenticado y activo
    - La reserva debe existir
    - El usuario debe ser el conductor o el pasajero de la reserva

    **Características:**
    - Chat simulado entre conductor y pasajero
    - Solo el conductor y el pasajero pueden enviar mensajes
    - Los mensajes son privados y solo visibles para conductor y pasajero
    - Los mensajes se marcan automáticamente como leídos cuando se leen

    **Ejemplo de uso:**
    ```
    POST /api/v1/trips/bookings/5/chat
    Authorization: Bearer <token>
    {
        "message": "Hola, ¿a qué hora pasas a recogerme?"
    }
    ```
    """
    # 1. Validar que la reserva existe
    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise EntityNotFound("Booking", booking_id)

    # 2. Obtener el trayecto
    trip = await trip_repo.get_by_id(booking.trip_id)
    if not trip:
        raise EntityNotFound("Trip", booking.trip_id)

    # 3. Validar que el usuario es el conductor o el pasajero
    is_driver = trip.driver_id == current_user.id
    is_passenger = booking.passenger_id == current_user.id

    if not (is_driver or is_passenger):
        raise Forbidden("Solo el conductor o el pasajero pueden enviar mensajes en este chat")

    # 4. Crear el mensaje
    chat_message = ChatMessage(
        booking_id=booking_id,
        sender_id=current_user.id,
        message=payload.message.strip()
    )

    created_message = await chat_repo.create(chat_message)

    return ChatMessageResponse.model_validate(created_message)


@router.get("/bookings/{booking_id}/chat", response_model=ChatConversationResponse)
async def get_chat_conversation(
    booking_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    chat_repo: Annotated[IChatRepository, Depends(get_chat_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    skip: int = Query(0, ge=0, description="Número de mensajes a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de mensajes")
):
    """
    Obtener conversación de chat de una reserva (RF-BONUS-004).

    **Endpoint:** `GET /trips/bookings/{booking_id}/chat`

    **Requisitos:**
    - Usuario autenticado y activo
    - La reserva debe existir
    - El usuario debe ser el conductor o el pasajero de la reserva

    **Características:**
    - Retorna todos los mensajes de la conversación
    - Los mensajes están ordenados cronológicamente (más antiguos primero)
    - Marca automáticamente los mensajes como leídos cuando se obtienen
    - Incluye contador de mensajes no leídos
    - Soporta paginación

    **Ejemplo de uso:**
    ```
    GET /api/v1/trips/bookings/5/chat
    Authorization: Bearer <token>
    ```

    **Respuesta:**
    - booking_id: ID de la reserva
    - messages: Lista de mensajes de la conversación
    - total_messages: Total de mensajes en la conversación
    - unread_count: Número de mensajes no leídos del otro usuario
    """
    # 1. Validar que la reserva existe
    booking = await booking_repo.get_by_id(booking_id)
    if not booking:
        raise EntityNotFound("Booking", booking_id)

    # 2. Obtener el trayecto
    trip = await trip_repo.get_by_id(booking.trip_id)
    if not trip:
        raise EntityNotFound("Trip", booking.trip_id)

    # 3. Validar que el usuario es el conductor o el pasajero
    is_driver = trip.driver_id == current_user.id
    is_passenger = booking.passenger_id == current_user.id

    if not (is_driver or is_passenger):
        raise Forbidden("Solo el conductor o el pasajero pueden ver este chat")

    # 4. Obtener mensajes de la conversación
    messages = await chat_repo.get_by_booking(booking_id, skip=skip, limit=limit)

    # 5. Contar mensajes no leídos
    unread_count = await chat_repo.get_unread_count(booking_id, current_user.id)

    # 6. Marcar mensajes como leídos
    await chat_repo.mark_as_read(booking_id, current_user.id)

    return ChatConversationResponse(
        booking_id=booking_id,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        total_messages=len(messages),
        unread_count=unread_count
    )


@router.delete("/chat/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_message(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    chat_repo: Annotated[IChatRepository, Depends(get_chat_repository)]
):
    """
    Eliminar mensaje de chat (RF-BONUS-004).

    **Endpoint:** `DELETE /trips/chat/{message_id}`

    **Requisitos:**
    - Usuario autenticado y activo
    - El mensaje debe existir
    - Solo el remitente del mensaje puede eliminarlo

    **Soft delete:** El mensaje se marca como is_deleted=True

    **Ejemplo de uso:**
    ```
    DELETE /api/v1/trips/chat/10
    Authorization: Bearer <token>
    ```
    """
    # 1. Obtener el mensaje
    message = await chat_repo.get_by_id(message_id)
    if not message:
        raise EntityNotFound("Message", message_id)

    # 2. Validar que el usuario es el remitente
    if message.sender_id != current_user.id:
        raise Forbidden("Solo puedes eliminar tus propios mensajes")

    # 3. Eliminar el mensaje (soft delete)
    success = await chat_repo.delete(message_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar mensaje"
        )

    return None
