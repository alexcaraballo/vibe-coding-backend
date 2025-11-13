"""Chat repository interface (contract)."""
from abc import ABC, abstractmethod
from typing import Optional
from apps.trips.domain.models import ChatMessage


class IChatRepository(ABC):
    """Contrato para el repositorio de mensajes de chat."""

    @abstractmethod
    async def create(self, message: ChatMessage) -> ChatMessage:
        """
        Crea un nuevo mensaje de chat.
        Retorna el mensaje con id asignado.
        """
        pass

    @abstractmethod
    async def get_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """Obtiene mensaje por ID."""
        pass

    @abstractmethod
    async def get_by_booking(
        self,
        booking_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[ChatMessage]:
        """Obtiene todos los mensajes de una reserva (chat conversation)."""
        pass

    @abstractmethod
    async def get_unread_count(
        self,
        booking_id: int,
        user_id: int
    ) -> int:
        """Cuenta mensajes no leídos de un usuario en una conversación."""
        pass

    @abstractmethod
    async def mark_as_read(
        self,
        booking_id: int,
        user_id: int
    ) -> int:
        """
        Marca todos los mensajes de una conversación como leídos para un usuario.
        Retorna el número de mensajes marcados.
        """
        pass

    @abstractmethod
    async def delete(self, message_id: int) -> bool:
        """Elimina mensaje (soft delete)."""
        pass
