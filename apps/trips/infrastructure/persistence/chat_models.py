"""Chat ORM models with SQLAlchemy 2.0."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base
from apps.trips.domain.models import ChatMessage


class ChatMessageORM(Base):
    """
    SQLAlchemy ORM model for chat_messages table.
    Maps between database and domain ChatMessage entity.
    """
    __tablename__ = "chat_messages"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    booking_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Message content
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Read status
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    # Metadata
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def to_domain(self) -> ChatMessage:
        """Convert ORM model to domain entity."""
        return ChatMessage(
            id=self.id,
            booking_id=self.booking_id,
            sender_id=self.sender_id,
            message=self.message,
            sent_at=self.sent_at,
            is_read=self.is_read,
            read_at=self.read_at,
            is_deleted=self.is_deleted
        )

    @staticmethod
    def from_domain(message: ChatMessage) -> "ChatMessageORM":
        """Convert domain entity to ORM model."""
        return ChatMessageORM(
            id=message.id,
            booking_id=message.booking_id,
            sender_id=message.sender_id,
            message=message.message,
            sent_at=message.sent_at,
            is_read=message.is_read,
            read_at=message.read_at,
            is_deleted=message.is_deleted
        )
