"""Chat repository implementation with SQLAlchemy."""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from sqlalchemy.exc import SQLAlchemyError

from apps.trips.domain.models import ChatMessage
from apps.trips.domain.repositories.chat_repository import IChatRepository
from apps.trips.infrastructure.persistence.chat_models import ChatMessageORM


class ChatRepository(IChatRepository):
    """Implementación SQLAlchemy del repositorio de mensajes de chat."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def create(self, message: ChatMessage) -> ChatMessage:
        """Create new chat message in database."""
        try:
            message_orm = ChatMessageORM.from_domain(message)
            self._session.add(message_orm)
            await self._session.commit()
            await self._session.refresh(message_orm)
            return message_orm.to_domain()
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error creating chat message: {str(e)}")

    async def get_by_id(self, message_id: int) -> Optional[ChatMessage]:
        """Get chat message by ID."""
        try:
            result = await self._session.execute(
                select(ChatMessageORM).where(ChatMessageORM.id == message_id)
            )
            message_orm = result.scalar_one_or_none()
            return message_orm.to_domain() if message_orm else None
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting chat message by id: {str(e)}")

    async def get_by_booking(
        self,
        booking_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list[ChatMessage]:
        """Get all messages for a booking (conversation)."""
        try:
            query = (
                select(ChatMessageORM)
                .where(
                    ChatMessageORM.booking_id == booking_id,
                    ChatMessageORM.is_deleted == False
                )
                .offset(skip)
                .limit(limit)
                .order_by(ChatMessageORM.sent_at.asc())  # Oldest first for chat
            )

            result = await self._session.execute(query)
            message_orms = result.scalars().all()
            return [message_orm.to_domain() for message_orm in message_orms]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error getting messages by booking: {str(e)}")

    async def get_unread_count(
        self,
        booking_id: int,
        user_id: int
    ) -> int:
        """Count unread messages for a user in a conversation."""
        try:
            query = (
                select(func.count(ChatMessageORM.id))
                .where(
                    and_(
                        ChatMessageORM.booking_id == booking_id,
                        ChatMessageORM.sender_id != user_id,  # Messages from other user
                        ChatMessageORM.is_read == False,
                        ChatMessageORM.is_deleted == False
                    )
                )
            )

            result = await self._session.execute(query)
            count = result.scalar()
            return count or 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Error counting unread messages: {str(e)}")

    async def mark_as_read(
        self,
        booking_id: int,
        user_id: int
    ) -> int:
        """Mark all messages in a conversation as read for a user."""
        try:
            stmt = (
                update(ChatMessageORM)
                .where(
                    and_(
                        ChatMessageORM.booking_id == booking_id,
                        ChatMessageORM.sender_id != user_id,  # Messages from other user
                        ChatMessageORM.is_read == False,
                        ChatMessageORM.is_deleted == False
                    )
                )
                .values(is_read=True, read_at=datetime.utcnow())
            )

            result = await self._session.execute(stmt)
            await self._session.commit()
            return result.rowcount
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error marking messages as read: {str(e)}")

    async def delete(self, message_id: int) -> bool:
        """Delete message (soft delete)."""
        try:
            stmt = (
                update(ChatMessageORM)
                .where(ChatMessageORM.id == message_id)
                .values(is_deleted=True)
            )

            result = await self._session.execute(stmt)
            await self._session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            await self._session.rollback()
            raise RuntimeError(f"Error deleting message: {str(e)}")
