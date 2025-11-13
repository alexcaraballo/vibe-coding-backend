# FastAPI Implementation Plan: Chat Simulado (Bonus Feature)

**Status**: READY
**Priority**: BONUS/OPTIONAL
**Version**: 1.0.0
**Last Updated**: 2025-11-13
**Related Docs**:
- `.claude/plans/11-RF-BONUS-004-chat-simulado.md`
- Depends on: RF-003 (Bookings), RF-BONUS-003 (Visualización Reservas)

---

## Summary

This implementation plan details a **simple HTTP polling-based in-app messaging system** for the carpooling platform, allowing drivers and passengers to communicate within booking contexts. The chat uses **SQLite3 + SQLAlchemy async** for data persistence, avoiding the complexity of WebSockets for MVP while maintaining a clear upgrade path.

**Key Characteristics:**
- REST-based polling architecture (no WebSockets in MVP)
- Messages organized by booking_id (thread per booking)
- Authorization: only booking participants can access messages
- SQLAlchemy async ORM with proper relationship mapping
- Alembic migrations for schema versioning
- Read receipts and unread message tracking
- System messages for automated notifications
- Documented WebSocket upgrade path for v2

**Polling Limitations:**
- 2-5 second latency (client polls every 3-5 seconds)
- Increased server load from frequent HTTP requests
- No push notifications or real-time delivery
- Requires active client to receive messages

---

## Architecture Mapping

### Domain → FastAPI Mapping

| Domain Concept | FastAPI Construct | Location | Notes |
|---------------|------------------|----------|-------|
| Message (entity) | SQLAlchemy ORM Model | `domain/models.py` | Message table with FK to bookings and users |
| Conversation (aggregate) | SQLAlchemy ORM Model | `domain/models.py` | Conversation table (optional, can use booking_id directly) |
| Message thread | Query by booking_id | `adapters/repos/message_repository.py` | Group messages by booking |
| Send message (command) | POST endpoint | `entrypoints/http/routers/chat.py` | Create new message |
| Get messages (query) | GET endpoint | `entrypoints/http/routers/chat.py` | Retrieve messages with polling |
| Authorization check | Dependency | `entrypoints/http/dependencies.py` | Verify user in booking participants |
| Read receipts | Many-to-many table | `domain/models.py` | message_read_receipts join table |
| System notifications | Message type enum | `domain/models.py` | MessageType.SYSTEM |

### Layer Responsibilities

- **Domain Layer** (`apps/chat/domain/`):
  - SQLAlchemy ORM models: Message, Conversation (optional), MessageReadReceipt
  - Enums: MessageType (TEXT, SYSTEM)
  - Repository interfaces: IMessageRepository, IConversationRepository
  - No business logic (pure data models)

- **Application Layer** (`apps/chat/application/`):
  - ChatService: Business logic for sending messages, authorization, read receipts
  - Commands: SendMessageCommand, MarkAsReadCommand
  - Queries: GetMessagesQuery, GetConversationsQuery
  - Orchestrates domain and adapter layers

- **Adapter Layer** (`apps/chat/adapters/`):
  - MessageRepository: SQLAlchemy async repository implementation
  - ConversationRepository: SQLAlchemy async repository implementation
  - Integration with BookingRepository for authorization

- **HTTP Entrypoints** (`apps/chat/entrypoints/http/`):
  - FastAPI routers: chat_router
  - Pydantic request/response schemas (DTOs)
  - Dependency injection: get_chat_service, get_current_user_in_booking
  - Authorization middleware: verify_booking_participant

---

## File Actions

### Create New Files

```
apps/chat/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── models.py                          # Message, Conversation ORM models
│   └── repositories/
│       ├── __init__.py
│       ├── message_repository.py          # IMessageRepository interface
│       └── conversation_repository.py     # IConversationRepository interface
├── application/
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── chat_service.py                # ChatService business logic
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── send_message.py                # SendMessageCommand
│   │   └── mark_as_read.py                # MarkAsReadCommand
│   └── queries/
│       ├── __init__.py
│       ├── get_messages.py                # GetMessagesQuery
│       └── get_conversations.py           # GetConversationsQuery
├── adapters/
│   ├── __init__.py
│   └── repositories/
│       ├── __init__.py
│       ├── message_repository.py          # MessageRepository implementation
│       └── conversation_repository.py     # ConversationRepository implementation
└── entrypoints/
    ├── __init__.py
    └── http/
        ├── __init__.py
        ├── routers/
        │   ├── __init__.py
        │   └── chat.py                    # Chat API endpoints
        ├── dependencies.py                # DI for chat services
        └── schemas/
            ├── __init__.py
            ├── requests.py                # SendMessageRequest
            └── responses.py               # MessageResponse, ConversationResponse

tests/chat/
├── __init__.py
├── test_message_repository.py             # Repository tests
├── test_chat_service.py                   # Service tests
├── test_chat_api.py                       # Integration tests
└── test_authorization.py                  # Authorization tests
```

### Modify Existing Files

- `alembic/versions/`: Add new migration for chat tables
- `apps/bookings/application/services/booking_service.py`: Integrate chat notifications
- `main.py`: Register chat router
- `config/database.py`: Ensure async session factory configured

---

## API Endpoints

### Summary Table

| Method | Path | Request Model | Response Model | Use Case | Auth |
|--------|------|--------------|----------------|----------|------|
| GET | `/api/v1/chat/conversations` | Query params | `List[ConversationResponse]` | List user's conversations | Required |
| GET | `/api/v1/chat/bookings/{booking_id}/messages` | Query params (since, skip, limit) | `List[MessageResponse]` | Get messages with polling | Required + Participant |
| POST | `/api/v1/chat/bookings/{booking_id}/messages` | `SendMessageRequest` | `MessageResponse` | Send message to booking thread | Required + Participant |
| POST | `/api/v1/chat/bookings/{booking_id}/mark-read` | None | 204 No Content | Mark all messages as read | Required + Participant |
| GET | `/api/v1/chat/bookings/{booking_id}/unread-count` | None | `UnreadCountResponse` | Get unread message count | Required + Participant |

### Endpoint Details

#### 1. GET /api/v1/chat/conversations

**Description**: List all conversations for the authenticated user (bookings with messages).

**Query Parameters:**
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=100, max=500): Pagination limit

**Response 200:**
```json
[
  {
    "booking_id": "uuid",
    "trip_id": "uuid",
    "participant_ids": ["user1", "user2"],
    "total_messages": 25,
    "unread_count": 3,
    "last_message_at": "2025-11-13T10:30:00Z",
    "last_message_preview": "¿A qué hora salimos?"
  }
]
```

**Authorization**: User must be authenticated

---

#### 2. GET /api/v1/chat/bookings/{booking_id}/messages

**Description**: Get messages for a booking thread. Supports polling by providing `since` timestamp.

**Path Parameters:**
- `booking_id` (UUID): Booking identifier

**Query Parameters:**
- `since` (datetime, optional): Only return messages after this timestamp (for polling)
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=50, max=200): Pagination limit

**Response 200:**
```json
{
  "booking_id": "uuid",
  "messages": [
    {
      "id": "uuid",
      "booking_id": "uuid",
      "sender_id": "uuid",
      "sender_name": "Juan Pérez",
      "content": "¿A qué hora salimos?",
      "message_type": "text",
      "created_at": "2025-11-13T10:30:00Z",
      "is_read": false,
      "read_by_user_ids": []
    }
  ],
  "has_more": false
}
```

**Authorization**: User must be booking participant (driver or passenger)

**Polling Usage:**
```javascript
// Client polls every 3-5 seconds
setInterval(async () => {
  const since = lastMessageTimestamp;
  const response = await fetch(`/api/v1/chat/bookings/${bookingId}/messages?since=${since}`);
  const data = await response.json();
  // Display new messages
}, 3000);
```

---

#### 3. POST /api/v1/chat/bookings/{booking_id}/messages

**Description**: Send a new message to a booking thread.

**Path Parameters:**
- `booking_id` (UUID): Booking identifier

**Request Body:**
```json
{
  "content": "¿A qué hora salimos?",
  "message_type": "text"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "booking_id": "uuid",
  "sender_id": "uuid",
  "sender_name": "Juan Pérez",
  "content": "¿A qué hora salimos?",
  "message_type": "text",
  "created_at": "2025-11-13T10:30:00Z",
  "is_read": false,
  "read_by_user_ids": []
}
```

**Authorization**: User must be booking participant

---

#### 4. POST /api/v1/chat/bookings/{booking_id}/mark-read

**Description**: Mark all messages in booking thread as read by current user.

**Path Parameters:**
- `booking_id` (UUID): Booking identifier

**Response 204**: No Content

**Authorization**: User must be booking participant

---

#### 5. GET /api/v1/chat/bookings/{booking_id}/unread-count

**Description**: Get count of unread messages in booking thread.

**Response 200:**
```json
{
  "booking_id": "uuid",
  "unread_count": 3
}
```

**Authorization**: User must be booking participant

---

## Data Persistence

### Database Schema Design

#### Messages Table

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL,
    sender_id UUID NOT NULL,
    sender_name VARCHAR(255) NOT NULL,  -- Denormalized for performance
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',  -- 'text' or 'system'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    CONSTRAINT fk_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_message_type CHECK (message_type IN ('text', 'system')),
    CONSTRAINT chk_content_length CHECK (LENGTH(content) >= 1 AND LENGTH(content) <= 1000)
);

-- Indexes for performance
CREATE INDEX idx_messages_booking_id ON messages(booking_id);
CREATE INDEX idx_messages_booking_created ON messages(booking_id, created_at);
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
```

#### Message Read Receipts Table (Many-to-Many)

```sql
CREATE TABLE message_read_receipts (
    message_id UUID NOT NULL,
    user_id UUID NOT NULL,
    read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (message_id, user_id),
    CONSTRAINT fk_message FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for counting unread messages
CREATE INDEX idx_read_receipts_user ON message_read_receipts(user_id);
```

#### Conversations Table (Optional - for metadata and optimization)

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id UUID NOT NULL UNIQUE,
    trip_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT fk_booking FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
    CONSTRAINT fk_trip FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_conversations_booking ON conversations(booking_id);
CREATE INDEX idx_conversations_trip ON conversations(trip_id);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at DESC);
```

**Note**: The `conversations` table is **optional**. We can use `booking_id` directly to group messages, but having a conversation aggregate provides:
- Faster metadata queries (total_messages, last_message_at)
- Easier to add conversation-level features (pinned, archived, etc.)
- Cleaner separation of concerns

**For MVP**: Consider starting without `conversations` table and adding it later if needed.

---

### SQLAlchemy ORM Models

**File**: `apps/chat/domain/models.py`

```python
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text,
    CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class MessageType(str, PyEnum):
    """Message type enumeration"""
    TEXT = "text"
    SYSTEM = "system"


class Message(Base):
    """
    Message entity.
    Represents a single message in a booking thread.
    """
    __tablename__ = "messages"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Denormalized for performance (avoid joins)
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, native_enum=False, length=20),
        default=MessageType.TEXT,
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="messages")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])
    read_receipts: Mapped[List["MessageReadReceipt"]] = relationship(
        "MessageReadReceipt",
        back_populates="message",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("LENGTH(content) >= 1 AND LENGTH(content) <= 1000", name="chk_content_length"),
        Index("idx_messages_booking_id", "booking_id"),
        Index("idx_messages_booking_created", "booking_id", "created_at"),
        Index("idx_messages_sender_id", "sender_id"),
    )

    def is_read_by(self, user_id: UUID) -> bool:
        """Check if message has been read by user"""
        return any(receipt.user_id == user_id for receipt in self.read_receipts)

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, sender={self.sender_name}, type={self.message_type})>"


class MessageReadReceipt(Base):
    """
    Message read receipt (many-to-many).
    Tracks which users have read which messages.
    """
    __tablename__ = "message_read_receipts"

    # Composite Primary Key
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Timestamp
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    message: Mapped["Message"] = relationship("Message", back_populates="read_receipts")
    user: Mapped["User"] = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_read_receipts_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<MessageReadReceipt(message_id={self.message_id}, user_id={self.user_id})>"


class Conversation(Base):
    """
    Conversation aggregate (optional).
    Provides metadata and optimization for booking message threads.

    NOTE: This table is optional for MVP. Consider implementing only if needed.
    """
    __tablename__ = "conversations"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    trip_id: Mapped[UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), nullable=False)

    # Metadata
    total_messages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    booking: Mapped["Booking"] = relationship("Booking", back_populates="conversation")
    trip: Mapped["Trip"] = relationship("Trip")

    # Indexes
    __table_args__ = (
        Index("idx_conversations_booking", "booking_id"),
        Index("idx_conversations_trip", "trip_id"),
        Index("idx_conversations_last_message", "last_message_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, booking_id={self.booking_id}, messages={self.total_messages})>"
```

**Relationship Updates Needed:**

**File**: `apps/bookings/domain/models.py`

```python
from sqlalchemy.orm import Mapped, relationship

class Booking(Base):
    # ... existing fields ...

    # Add relationship to messages
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="booking",
        cascade="all, delete-orphan"
    )

    # Optional: relationship to conversation
    conversation: Mapped[Optional["Conversation"]] = relationship(
        "Conversation",
        back_populates="booking",
        uselist=False
    )
```

---

### Repository Interfaces

**File**: `apps/chat/domain/repositories/message_repository.py`

```python
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from apps.chat.domain.models import Message


class IMessageRepository(ABC):
    """Message repository interface"""

    @abstractmethod
    async def create(self, message: Message) -> Message:
        """Create a new message"""
        pass

    @abstractmethod
    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """Get message by ID"""
        pass

    @abstractmethod
    async def get_by_booking(
        self,
        booking_id: UUID,
        skip: int = 0,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Message]:
        """
        Get messages for a booking thread.

        Args:
            booking_id: Booking identifier
            skip: Pagination offset
            limit: Pagination limit
            since: Only return messages after this timestamp (for polling)
        """
        pass

    @abstractmethod
    async def count_by_booking(self, booking_id: UUID) -> int:
        """Count total messages in booking thread"""
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: UUID, user_id: UUID) -> bool:
        """Mark message as read by user"""
        pass

    @abstractmethod
    async def count_unread_by_user(self, booking_id: UUID, user_id: UUID) -> int:
        """Count unread messages for user in booking thread"""
        pass

    @abstractmethod
    async def get_last_message(self, booking_id: UUID) -> Optional[Message]:
        """Get last message in booking thread"""
        pass
```

**File**: `apps/chat/domain/repositories/conversation_repository.py`

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from apps.chat.domain.models import Conversation


class IConversationRepository(ABC):
    """Conversation repository interface (optional)"""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation"""
        pass

    @abstractmethod
    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID"""
        pass

    @abstractmethod
    async def get_by_booking(self, booking_id: UUID) -> Optional[Conversation]:
        """Get conversation for booking"""
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """Get conversations for user (bookings where user is participant)"""
        pass

    @abstractmethod
    async def update(self, conversation: Conversation) -> Conversation:
        """Update conversation metadata"""
        pass
```

---

### Repository Implementations

**File**: `apps/chat/adapters/repositories/message_repository.py`

```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.chat.domain.models import Message, MessageReadReceipt
from apps.chat.domain.repositories.message_repository import IMessageRepository


class MessageRepository(IMessageRepository):
    """SQLAlchemy async implementation of message repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: Message) -> Message:
        """Create a new message"""
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """Get message by ID with read receipts"""
        query = (
            select(Message)
            .options(selectinload(Message.read_receipts))
            .where(Message.id == message_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_booking(
        self,
        booking_id: UUID,
        skip: int = 0,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Message]:
        """Get messages for booking thread with optional polling filter"""
        query = (
            select(Message)
            .options(selectinload(Message.read_receipts))
            .where(Message.booking_id == booking_id)
        )

        # Polling filter: only messages after timestamp
        if since:
            query = query.where(Message.created_at > since)

        query = query.order_by(Message.created_at.asc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_booking(self, booking_id: UUID) -> int:
        """Count total messages in booking thread"""
        query = select(func.count(Message.id)).where(Message.booking_id == booking_id)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def mark_as_read(self, message_id: UUID, user_id: UUID) -> bool:
        """Mark message as read by user (idempotent)"""
        # Check if already marked
        existing = await self.session.execute(
            select(MessageReadReceipt).where(
                and_(
                    MessageReadReceipt.message_id == message_id,
                    MessageReadReceipt.user_id == user_id
                )
            )
        )
        if existing.scalar_one_or_none():
            return False  # Already marked

        # Create read receipt
        receipt = MessageReadReceipt(message_id=message_id, user_id=user_id)
        self.session.add(receipt)
        await self.session.commit()
        return True

    async def count_unread_by_user(self, booking_id: UUID, user_id: UUID) -> int:
        """
        Count unread messages for user in booking thread.

        Logic: Messages in booking where:
        - sender_id != user_id (don't count own messages)
        - No read receipt for user_id
        """
        # Subquery: message IDs that user has read
        read_subquery = (
            select(MessageReadReceipt.message_id)
            .where(MessageReadReceipt.user_id == user_id)
        )

        # Main query: count messages not in read subquery
        query = (
            select(func.count(Message.id))
            .where(
                and_(
                    Message.booking_id == booking_id,
                    Message.sender_id != user_id,
                    Message.id.notin_(read_subquery)
                )
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_last_message(self, booking_id: UUID) -> Optional[Message]:
        """Get last message in booking thread"""
        query = (
            select(Message)
            .where(Message.booking_id == booking_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
```

**File**: `apps/chat/adapters/repositories/conversation_repository.py`

```python
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.chat.domain.models import Conversation
from apps.chat.domain.repositories.conversation_repository import IConversationRepository


class ConversationRepository(IConversationRepository):
    """SQLAlchemy async implementation of conversation repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation"""
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_by_id(self, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by ID"""
        query = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_booking(self, booking_id: UUID) -> Optional[Conversation]:
        """Get conversation for booking"""
        query = select(Conversation).where(Conversation.booking_id == booking_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Conversation]:
        """
        Get conversations for user.

        Note: Requires join with bookings to find user's conversations.
        User is participant if they are driver or passenger of the booking.
        """
        from apps.bookings.domain.models import Booking

        query = (
            select(Conversation)
            .join(Booking, Conversation.booking_id == Booking.id)
            .where(
                (Booking.driver_id == user_id) | (Booking.passenger_id == user_id)
            )
            .where(Conversation.is_active == True)
            .order_by(Conversation.last_message_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, conversation: Conversation) -> Conversation:
        """Update conversation metadata"""
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation
```

---

## Application Layer - Business Logic

**File**: `apps/chat/application/services/chat_service.py`

```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from apps.chat.domain.models import Message, MessageType
from apps.chat.domain.repositories.message_repository import IMessageRepository
from apps.chat.domain.repositories.conversation_repository import IConversationRepository
from apps.bookings.domain.repositories.booking_repository import IBookingRepository


class ChatService:
    """
    Chat business logic service.

    Responsibilities:
    - Authorization: verify user is booking participant
    - Message sending with validation
    - Read receipt management
    - System message generation
    - Conversation metadata updates
    """

    def __init__(
        self,
        message_repo: IMessageRepository,
        conversation_repo: Optional[IConversationRepository],
        booking_repo: IBookingRepository
    ):
        self.message_repo = message_repo
        self.conversation_repo = conversation_repo
        self.booking_repo = booking_repo

    async def verify_participant(self, booking_id: UUID, user_id: UUID) -> bool:
        """
        Verify user is participant in booking (driver or passenger).

        Raises:
            HTTPException 404: Booking not found
            HTTPException 403: User is not participant
        """
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking {booking_id} not found"
            )

        is_participant = (booking.driver_id == user_id or booking.passenger_id == user_id)
        if not is_participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this booking"
            )

        return True

    async def send_message(
        self,
        booking_id: UUID,
        sender_id: UUID,
        sender_name: str,
        content: str,
        message_type: MessageType = MessageType.TEXT
    ) -> Message:
        """
        Send a message to booking thread.

        Validations:
        - User is booking participant
        - Content is not empty and within length limit

        Side effects:
        - Updates conversation metadata (if using conversations table)
        """
        # Verify authorization
        await self.verify_participant(booking_id, sender_id)

        # Validate content
        content = content.strip()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content cannot be empty"
            )
        if len(content) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content cannot exceed 1000 characters"
            )

        # Create message
        message = Message(
            booking_id=booking_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            message_type=message_type
        )

        created_message = await self.message_repo.create(message)

        # Update conversation metadata (if using conversations)
        if self.conversation_repo:
            await self._update_conversation_metadata(booking_id)

        return created_message

    async def get_messages(
        self,
        booking_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Message]:
        """
        Get messages for booking thread.

        Args:
            since: For polling - only return messages after this timestamp
        """
        # Verify authorization
        await self.verify_participant(booking_id, user_id)

        return await self.message_repo.get_by_booking(
            booking_id, skip=skip, limit=limit, since=since
        )

    async def mark_all_as_read(self, booking_id: UUID, user_id: UUID) -> int:
        """
        Mark all messages in booking thread as read by user.

        Returns:
            Number of messages marked as read
        """
        # Verify authorization
        await self.verify_participant(booking_id, user_id)

        # Get all messages
        messages = await self.message_repo.get_by_booking(booking_id, limit=1000)

        # Mark each message that's not from user and not already read
        marked_count = 0
        for message in messages:
            if message.sender_id != user_id and not message.is_read_by(user_id):
                marked = await self.message_repo.mark_as_read(message.id, user_id)
                if marked:
                    marked_count += 1

        return marked_count

    async def get_unread_count(self, booking_id: UUID, user_id: UUID) -> int:
        """Get count of unread messages for user in booking thread"""
        # Verify authorization
        await self.verify_participant(booking_id, user_id)

        return await self.message_repo.count_unread_by_user(booking_id, user_id)

    async def send_system_message(
        self,
        booking_id: UUID,
        content: str
    ) -> Message:
        """
        Send system notification message.

        Examples:
        - "Juan Pérez joined the trip"
        - "Driver updated the departure time"

        Note: System messages do not require sender authorization.
        """
        message = Message(
            booking_id=booking_id,
            sender_id=UUID("00000000-0000-0000-0000-000000000000"),  # System UUID
            sender_name="System",
            content=content,
            message_type=MessageType.SYSTEM
        )

        created_message = await self.message_repo.create(message)

        # Update conversation metadata
        if self.conversation_repo:
            await self._update_conversation_metadata(booking_id)

        return created_message

    async def _update_conversation_metadata(self, booking_id: UUID) -> None:
        """Update conversation metadata (internal helper)"""
        if not self.conversation_repo:
            return

        conversation = await self.conversation_repo.get_by_booking(booking_id)
        if conversation:
            conversation.last_message_at = datetime.utcnow()
            conversation.total_messages = await self.message_repo.count_by_booking(booking_id)
            await self.conversation_repo.update(conversation)
```

---

## HTTP Entrypoints

### Pydantic Schemas (DTOs)

**File**: `apps/chat/entrypoints/http/schemas/requests.py`

```python
from pydantic import BaseModel, Field, field_validator

from apps.chat.domain.models import MessageType


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str = Field(..., min_length=1, max_length=1000)
    message_type: MessageType = Field(default=MessageType.TEXT)

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty after stripping"""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "content": "¿A qué hora salimos?",
                "message_type": "text"
            }
        }
```

**File**: `apps/chat/entrypoints/http/schemas/responses.py`

```python
from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Response model for a message"""
    id: UUID
    booking_id: UUID
    sender_id: UUID
    sender_name: str
    content: str
    message_type: str
    created_at: datetime
    is_read: bool = Field(description="Whether current user has read this message")
    read_by_user_ids: List[UUID] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MessagesResponse(BaseModel):
    """Response model for message list with pagination"""
    booking_id: UUID
    messages: List[MessageResponse]
    has_more: bool = Field(description="Whether more messages are available")


class UnreadCountResponse(BaseModel):
    """Response model for unread message count"""
    booking_id: UUID
    unread_count: int


class ConversationResponse(BaseModel):
    """Response model for a conversation summary"""
    booking_id: UUID
    trip_id: UUID
    participant_ids: List[UUID]
    total_messages: int
    unread_count: int
    last_message_at: datetime | None
    last_message_preview: str | None = Field(
        max_length=100,
        description="Preview of last message (truncated)"
    )

    class Config:
        from_attributes = True
```

---

### FastAPI Router

**File**: `apps/chat/entrypoints/http/routers/chat.py`

```python
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from apps.chat.application.services.chat_service import ChatService
from apps.chat.entrypoints.http.dependencies import get_chat_service
from apps.chat.entrypoints.http.schemas.requests import SendMessageRequest
from apps.chat.entrypoints.http.schemas.responses import (
    MessageResponse,
    MessagesResponse,
    UnreadCountResponse,
    ConversationResponse
)
from apps.users.domain.models import User
from apps.users.entrypoints.http.dependencies import get_current_user


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    summary="List user's conversations"
)
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit")
):
    """
    List all conversations (booking threads) for the authenticated user.

    Returns bookings where user is driver or passenger, with message metadata.
    """
    # Note: This endpoint requires conversation_repo implementation
    # For MVP without conversations table, this can return bookings with messages directly
    if not chat_service.conversation_repo:
        return []  # Or implement alternative using booking queries

    conversations = await chat_service.conversation_repo.get_by_user(
        current_user.id, skip=skip, limit=limit
    )

    responses = []
    for conv in conversations:
        unread_count = await chat_service.get_unread_count(conv.booking_id, current_user.id)
        last_message = await chat_service.message_repo.get_last_message(conv.booking_id)

        responses.append(ConversationResponse(
            booking_id=conv.booking_id,
            trip_id=conv.trip_id,
            participant_ids=[],  # Can be populated from booking
            total_messages=conv.total_messages,
            unread_count=unread_count,
            last_message_at=conv.last_message_at,
            last_message_preview=last_message.content[:100] if last_message else None
        ))

    return responses


@router.get(
    "/bookings/{booking_id}/messages",
    response_model=MessagesResponse,
    summary="Get messages for booking (with polling support)"
)
async def get_messages(
    booking_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    since: Optional[datetime] = Query(None, description="Only return messages after this timestamp (for polling)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit")
):
    """
    Get messages for a booking thread.

    **Polling Usage:**
    - Client polls every 3-5 seconds with `since` parameter
    - Pass the timestamp of the last received message
    - Only new messages after that timestamp will be returned

    **Example:**
    ```javascript
    setInterval(async () => {
        const since = lastMessageTimestamp;
        const response = await fetch(`/api/v1/chat/bookings/${bookingId}/messages?since=${since}`);
        const data = await response.json();
        displayNewMessages(data.messages);
    }, 3000);
    ```
    """
    messages = await chat_service.get_messages(
        booking_id,
        current_user.id,
        skip=skip,
        limit=limit,
        since=since
    )

    # Check if more messages are available
    total_messages = await chat_service.message_repo.count_by_booking(booking_id)
    has_more = (skip + limit) < total_messages

    # Transform to response DTOs
    message_responses = [
        MessageResponse(
            id=msg.id,
            booking_id=msg.booking_id,
            sender_id=msg.sender_id,
            sender_name=msg.sender_name,
            content=msg.content,
            message_type=msg.message_type.value,
            created_at=msg.created_at,
            is_read=msg.is_read_by(current_user.id),
            read_by_user_ids=[receipt.user_id for receipt in msg.read_receipts]
        )
        for msg in messages
    ]

    return MessagesResponse(
        booking_id=booking_id,
        messages=message_responses,
        has_more=has_more
    )


@router.post(
    "/bookings/{booking_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message"
)
async def send_message(
    booking_id: UUID,
    payload: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    Send a message to a booking thread.

    Only booking participants (driver or passenger) can send messages.
    """
    message = await chat_service.send_message(
        booking_id=booking_id,
        sender_id=current_user.id,
        sender_name=current_user.name,  # Assuming User has name field
        content=payload.content,
        message_type=payload.message_type
    )

    return MessageResponse(
        id=message.id,
        booking_id=message.booking_id,
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        content=message.content,
        message_type=message.message_type.value,
        created_at=message.created_at,
        is_read=False,
        read_by_user_ids=[]
    )


@router.post(
    "/bookings/{booking_id}/mark-read",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Mark all messages as read"
)
async def mark_messages_read(
    booking_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    Mark all messages in booking thread as read by current user.

    Idempotent - can be called multiple times safely.
    """
    await chat_service.mark_all_as_read(booking_id, current_user.id)
    return None


@router.get(
    "/bookings/{booking_id}/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread message count"
)
async def get_unread_count(
    booking_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    Get count of unread messages for current user in booking thread.
    """
    unread_count = await chat_service.get_unread_count(booking_id, current_user.id)

    return UnreadCountResponse(
        booking_id=booking_id,
        unread_count=unread_count
    )
```

---

### Dependency Injection

**File**: `apps/chat/entrypoints/http/dependencies.py`

```python
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_session
from apps.chat.adapters.repositories.message_repository import MessageRepository
from apps.chat.adapters.repositories.conversation_repository import ConversationRepository
from apps.chat.application.services.chat_service import ChatService
from apps.bookings.adapters.repositories.booking_repository import BookingRepository


async def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> ChatService:
    """
    Dependency injection for ChatService.

    Creates repositories with current async session and injects into service.
    """
    message_repo = MessageRepository(session)
    conversation_repo = ConversationRepository(session)  # Optional: can be None for MVP
    booking_repo = BookingRepository(session)

    return ChatService(
        message_repo=message_repo,
        conversation_repo=conversation_repo,  # or None
        booking_repo=booking_repo
    )
```

---

## Integration with Booking Service

When a booking is created, automatically send a system message to notify participants.

**File**: `apps/bookings/application/services/booking_service.py`

```python
# Add to existing BookingService

from apps.chat.application.services.chat_service import ChatService

class BookingService:
    def __init__(
        self,
        booking_repo: IBookingRepository,
        trip_repo: ITripRepository,
        chat_service: Optional[ChatService] = None  # Inject chat service
    ):
        self.booking_repo = booking_repo
        self.trip_repo = trip_repo
        self.chat_service = chat_service

    async def create_booking(
        self,
        trip_id: UUID,
        passenger_id: UUID,
        # ... other params
    ) -> Booking:
        # ... existing booking creation logic ...

        booking = await self.booking_repo.create(...)

        # Send system notification to chat (if chat service available)
        if self.chat_service:
            try:
                passenger = await self.user_repo.get_by_id(passenger_id)
                await self.chat_service.send_system_message(
                    booking_id=booking.id,
                    content=f"{passenger.name} joined the trip"
                )
            except Exception as e:
                # Log error but don't fail booking creation
                print(f"Failed to send chat notification: {e}")

        return booking
```

---

## Alembic Migration

**File**: `alembic/versions/{timestamp}_add_chat_tables.py`

```python
"""Add chat tables for messaging feature

Revision ID: {generated_id}
Revises: {previous_revision}
Create Date: 2025-11-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '{generated_id}'
down_revision = '{previous_revision}'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_name', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='text'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("message_type IN ('text', 'system')", name='chk_message_type'),
        sa.CheckConstraint("LENGTH(content) >= 1 AND LENGTH(content) <= 1000", name='chk_content_length'),
    )

    # Create indexes for messages
    op.create_index('idx_messages_booking_id', 'messages', ['booking_id'])
    op.create_index('idx_messages_booking_created', 'messages', ['booking_id', 'created_at'])
    op.create_index('idx_messages_sender_id', 'messages', ['sender_id'])

    # Create message_read_receipts table
    op.create_table(
        'message_read_receipts',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('read_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create index for read receipts
    op.create_index('idx_read_receipts_user', 'message_read_receipts', ['user_id'])

    # Optional: Create conversations table (can be added later if needed)
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('trip_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_messages', sa.Integer, nullable=False, server_default='0'),
        sa.Column('last_message_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
    )

    # Create indexes for conversations
    op.create_index('idx_conversations_booking', 'conversations', ['booking_id'])
    op.create_index('idx_conversations_trip', 'conversations', ['trip_id'])
    op.create_index('idx_conversations_last_message', 'conversations', ['last_message_at'])


def downgrade() -> None:
    op.drop_index('idx_conversations_last_message', table_name='conversations')
    op.drop_index('idx_conversations_trip', table_name='conversations')
    op.drop_index('idx_conversations_booking', table_name='conversations')
    op.drop_table('conversations')

    op.drop_index('idx_read_receipts_user', table_name='message_read_receipts')
    op.drop_table('message_read_receipts')

    op.drop_index('idx_messages_sender_id', table_name='messages')
    op.drop_index('idx_messages_booking_created', table_name='messages')
    op.drop_index('idx_messages_booking_id', table_name='messages')
    op.drop_table('messages')
```

**Migration Commands:**

```bash
# Generate migration
alembic revision --autogenerate -m "Add chat tables for messaging feature"

# Review migration file and adjust if needed
# ...

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Testing Strategy

### Integration Tests

**File**: `tests/chat/test_chat_api.py`

```python
import pytest
from httpx import AsyncClient
from datetime import datetime
from uuid import uuid4

from apps.chat.domain.models import MessageType


@pytest.mark.asyncio
async def test_send_message_success(
    async_client: AsyncClient,
    auth_headers: dict,
    test_booking: Booking
):
    """Test sending a message to booking thread"""
    response = await async_client.post(
        f"/api/v1/chat/bookings/{test_booking.id}/messages",
        headers=auth_headers,
        json={"content": "¿A qué hora salimos?", "message_type": "text"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "¿A qué hora salimos?"
    assert data["message_type"] == "text"
    assert data["booking_id"] == str(test_booking.id)


@pytest.mark.asyncio
async def test_send_message_unauthorized(
    async_client: AsyncClient,
    auth_headers_other_user: dict,
    test_booking: Booking
):
    """Test sending message fails if user is not booking participant"""
    response = await async_client.post(
        f"/api/v1/chat/bookings/{test_booking.id}/messages",
        headers=auth_headers_other_user,
        json={"content": "Hello"}
    )

    assert response.status_code == 403
    assert "not a participant" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_messages_with_polling(
    async_client: AsyncClient,
    auth_headers: dict,
    test_booking_with_messages: Booking
):
    """Test polling for new messages using since parameter"""
    # Get initial messages
    response1 = await async_client.get(
        f"/api/v1/chat/bookings/{test_booking_with_messages.id}/messages",
        headers=auth_headers
    )
    assert response1.status_code == 200
    data1 = response1.json()
    initial_count = len(data1["messages"])

    # Send new message
    await async_client.post(
        f"/api/v1/chat/bookings/{test_booking_with_messages.id}/messages",
        headers=auth_headers,
        json={"content": "New message"}
    )

    # Poll with since parameter
    last_message_time = data1["messages"][-1]["created_at"] if data1["messages"] else None
    response2 = await async_client.get(
        f"/api/v1/chat/bookings/{test_booking_with_messages.id}/messages",
        headers=auth_headers,
        params={"since": last_message_time}
    )

    data2 = response2.json()
    assert len(data2["messages"]) == 1  # Only new message
    assert data2["messages"][0]["content"] == "New message"


@pytest.mark.asyncio
async def test_mark_messages_as_read(
    async_client: AsyncClient,
    auth_headers: dict,
    test_booking_with_messages: Booking
):
    """Test marking messages as read"""
    # Get unread count before
    response1 = await async_client.get(
        f"/api/v1/chat/bookings/{test_booking_with_messages.id}/unread-count",
        headers=auth_headers
    )
    unread_before = response1.json()["unread_count"]
    assert unread_before > 0

    # Mark as read
    response2 = await async_client.post(
        f"/api/v1/chat/bookings/{test_booking_with_messages.id}/mark-read",
        headers=auth_headers
    )
    assert response2.status_code == 204

    # Get unread count after
    response3 = await async_client.get(
        f"/api/v1/chat/bookings/{test_booking_with_messages.id}/unread-count",
        headers=auth_headers
    )
    unread_after = response3.json()["unread_count"]
    assert unread_after == 0


@pytest.mark.asyncio
async def test_system_message_creation(
    async_client: AsyncClient,
    chat_service: ChatService,
    test_booking: Booking
):
    """Test creating system notification message"""
    message = await chat_service.send_system_message(
        booking_id=test_booking.id,
        content="User joined the trip"
    )

    assert message.message_type == MessageType.SYSTEM
    assert message.sender_name == "System"
    assert message.content == "User joined the trip"


@pytest.mark.asyncio
async def test_empty_message_validation(
    async_client: AsyncClient,
    auth_headers: dict,
    test_booking: Booking
):
    """Test that empty messages are rejected"""
    response = await async_client.post(
        f"/api/v1/chat/bookings/{test_booking.id}/messages",
        headers=auth_headers,
        json={"content": "   "}  # Only whitespace
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_message_length_validation(
    async_client: AsyncClient,
    auth_headers: dict,
    test_booking: Booking
):
    """Test that messages exceeding 1000 chars are rejected"""
    long_content = "a" * 1001
    response = await async_client.post(
        f"/api/v1/chat/bookings/{test_booking.id}/messages",
        headers=auth_headers,
        json={"content": long_content}
    )

    assert response.status_code == 400
```

### Repository Tests

**File**: `tests/chat/test_message_repository.py`

```python
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from apps.chat.adapters.repositories.message_repository import MessageRepository
from apps.chat.domain.models import Message, MessageType


@pytest.mark.asyncio
async def test_create_message(message_repo: MessageRepository, test_booking: Booking):
    """Test creating a message"""
    message = Message(
        booking_id=test_booking.id,
        sender_id=test_booking.driver_id,
        sender_name="Driver",
        content="Test message",
        message_type=MessageType.TEXT
    )

    created = await message_repo.create(message)
    assert created.id is not None
    assert created.content == "Test message"


@pytest.mark.asyncio
async def test_get_by_booking(message_repo: MessageRepository, test_booking_with_messages: Booking):
    """Test retrieving messages by booking"""
    messages = await message_repo.get_by_booking(test_booking_with_messages.id)

    assert len(messages) > 0
    assert all(msg.booking_id == test_booking_with_messages.id for msg in messages)
    # Verify chronological order
    assert messages == sorted(messages, key=lambda m: m.created_at)


@pytest.mark.asyncio
async def test_get_by_booking_with_since(
    message_repo: MessageRepository,
    test_booking_with_messages: Booking
):
    """Test polling filter with since parameter"""
    # Get all messages
    all_messages = await message_repo.get_by_booking(test_booking_with_messages.id)

    # Get messages since middle timestamp
    since_time = all_messages[len(all_messages) // 2].created_at
    recent_messages = await message_repo.get_by_booking(
        test_booking_with_messages.id,
        since=since_time
    )

    assert len(recent_messages) < len(all_messages)
    assert all(msg.created_at > since_time for msg in recent_messages)


@pytest.mark.asyncio
async def test_mark_as_read(message_repo: MessageRepository, test_message: Message, test_user: User):
    """Test marking message as read"""
    # Initially not read
    assert not test_message.is_read_by(test_user.id)

    # Mark as read
    marked = await message_repo.mark_as_read(test_message.id, test_user.id)
    assert marked is True

    # Verify read
    message = await message_repo.get_by_id(test_message.id)
    assert message.is_read_by(test_user.id)

    # Idempotent - marking again returns False
    marked_again = await message_repo.mark_as_read(test_message.id, test_user.id)
    assert marked_again is False


@pytest.mark.asyncio
async def test_count_unread_by_user(
    message_repo: MessageRepository,
    test_booking: Booking,
    test_user: User
):
    """Test counting unread messages for user"""
    # Create messages from other user
    for i in range(3):
        await message_repo.create(Message(
            booking_id=test_booking.id,
            sender_id=test_booking.driver_id,
            sender_name="Driver",
            content=f"Message {i}"
        ))

    # Count unread (should be 3)
    unread = await message_repo.count_unread_by_user(test_booking.id, test_user.id)
    assert unread == 3

    # Mark one as read
    messages = await message_repo.get_by_booking(test_booking.id)
    await message_repo.mark_as_read(messages[0].id, test_user.id)

    # Count again (should be 2)
    unread = await message_repo.count_unread_by_user(test_booking.id, test_user.id)
    assert unread == 2
```

### Authorization Tests

**File**: `tests/chat/test_authorization.py`

```python
import pytest
from fastapi import HTTPException

from apps.chat.application.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_verify_participant_as_driver(
    chat_service: ChatService,
    test_booking: Booking
):
    """Test driver can access booking chat"""
    result = await chat_service.verify_participant(test_booking.id, test_booking.driver_id)
    assert result is True


@pytest.mark.asyncio
async def test_verify_participant_as_passenger(
    chat_service: ChatService,
    test_booking: Booking
):
    """Test passenger can access booking chat"""
    result = await chat_service.verify_participant(test_booking.id, test_booking.passenger_id)
    assert result is True


@pytest.mark.asyncio
async def test_verify_participant_unauthorized(
    chat_service: ChatService,
    test_booking: Booking
):
    """Test non-participant cannot access booking chat"""
    random_user_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await chat_service.verify_participant(test_booking.id, random_user_id)

    assert exc_info.value.status_code == 403
    assert "not a participant" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_participant_nonexistent_booking(
    chat_service: ChatService
):
    """Test accessing nonexistent booking raises 404"""
    fake_booking_id = uuid4()
    user_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await chat_service.verify_participant(fake_booking_id, user_id)

    assert exc_info.value.status_code == 404
```

---

## Dependencies

### Required Python Packages

Add to `requirements.txt` or `pyproject.toml`:

```toml
[tool.poetry.dependencies]
# Core
fastapi = "^0.104.0"
uvicorn = "^0.24.0"

# Database
sqlalchemy = "^2.0.23"
aiosqlite = "^0.19.0"  # For SQLite async
alembic = "^1.12.0"

# Validation
pydantic = "^2.5.0"

# Testing
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
faker = "^20.0.0"  # For test data generation

# Optional: For production PostgreSQL
asyncpg = "^0.29.0"
```

**Why These Packages:**

- **aiosqlite**: Async SQLite driver for SQLAlchemy
- **sqlalchemy[asyncio]**: ORM with async support
- **alembic**: Database migration tool
- **pydantic**: Request/response validation and serialization
- **pytest-asyncio**: Async test support
- **httpx**: Async HTTP client for integration tests

---

## Implementation Checklist

### Phase 1: Database Schema (1 hour)

- [ ] Create SQLAlchemy ORM models (Message, MessageReadReceipt, Conversation)
- [ ] Define repository interfaces (IMessageRepository, IConversationRepository)
- [ ] Write Alembic migration for chat tables
- [ ] Run migration and verify schema in SQLite
- [ ] Add relationships to Booking model

### Phase 2: Repository Layer (1 hour)

- [ ] Implement MessageRepository with SQLAlchemy async
  - [ ] create()
  - [ ] get_by_id()
  - [ ] get_by_booking() with since parameter
  - [ ] mark_as_read()
  - [ ] count_unread_by_user()
- [ ] Implement ConversationRepository (optional for MVP)
- [ ] Write repository unit tests

### Phase 3: Business Logic (1 hour)

- [ ] Implement ChatService
  - [ ] verify_participant() authorization
  - [ ] send_message() with validation
  - [ ] get_messages() with polling support
  - [ ] mark_all_as_read()
  - [ ] get_unread_count()
  - [ ] send_system_message()
- [ ] Write service unit tests

### Phase 4: HTTP Entrypoints (1 hour)

- [ ] Create Pydantic request/response schemas
- [ ] Implement chat router endpoints
  - [ ] GET /conversations
  - [ ] GET /bookings/{id}/messages (with polling)
  - [ ] POST /bookings/{id}/messages
  - [ ] POST /bookings/{id}/mark-read
  - [ ] GET /bookings/{id}/unread-count
- [ ] Implement dependency injection (get_chat_service)
- [ ] Register router in main.py
- [ ] Test endpoints with Swagger UI

### Phase 5: Integration (30 minutes)

- [ ] Integrate with BookingService to send system messages
- [ ] Test end-to-end flow: booking → system message → chat
- [ ] Write integration tests

### Phase 6: Documentation & Testing (30 minutes)

- [ ] Document API in Swagger/OpenAPI
- [ ] Write client-side polling example (JavaScript)
- [ ] Create test fixtures and factories
- [ ] Run full test suite
- [ ] Document WebSocket upgrade path

### Total Estimated Time: 4-5 hours

---

## Open Questions

1. **Conversation Table**: Should we implement the optional `conversations` table in MVP, or start without it and add later if needed?
   - **Recommendation**: Start without it. Use `booking_id` directly for message threading. Add conversations table only if we need faster metadata queries or conversation-level features.

2. **Message Retention**: Should we implement message deletion or archiving?
   - **Recommendation**: No for MVP. All messages persist. Add in v2 if needed.

3. **File Attachments**: Should we support image/file uploads in chat?
   - **Recommendation**: No for MVP. Text-only messages. Add in v2 with S3/blob storage.

4. **Typing Indicators**: Should we implement "User is typing..." indicators?
   - **Recommendation**: No for MVP. Requires WebSockets or aggressive polling. Add in v2.

5. **Read Receipts Performance**: With many users, the read receipts table could grow large. Should we optimize?
   - **Recommendation**: Monitor in production. Consider adding indexes or denormalizing if needed.

6. **Database Choice**: Should we use PostgreSQL instead of SQLite for production?
   - **Recommendation**: SQLite is fine for MVP. For production with multiple users, migrate to PostgreSQL using the same SQLAlchemy models (minimal code changes).

---

## WebSocket Upgrade Path (v2 Enhancement)

### Current Limitations of Polling

**Polling Approach:**
- Client requests `/messages?since=timestamp` every 3-5 seconds
- Server returns new messages since last check
- Latency: 2-5 seconds depending on poll interval
- Server load: High (N users × polls per minute)

**Issues at Scale:**
- 100 users polling every 3s = ~2000 requests/min
- Unnecessary requests when no new messages
- Battery drain on mobile devices
- No push notifications

---

### WebSocket Migration Strategy

#### Step 1: Add WebSocket Support

**Install dependencies:**
```bash
pip install websockets python-socketio
```

**Create WebSocket manager:**

```python
# apps/chat/infrastructure/websocket/manager.py

from typing import Dict, Set
from uuid import UUID
from fastapi import WebSocket

class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""

    def __init__(self):
        # booking_id -> set of connected websockets
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, booking_id: UUID):
        await websocket.accept()
        if booking_id not in self.active_connections:
            self.active_connections[booking_id] = set()
        self.active_connections[booking_id].add(websocket)

    def disconnect(self, websocket: WebSocket, booking_id: UUID):
        if booking_id in self.active_connections:
            self.active_connections[booking_id].discard(websocket)

    async def broadcast_message(self, booking_id: UUID, message: dict):
        """Broadcast message to all connected clients in booking"""
        if booking_id in self.active_connections:
            for connection in self.active_connections[booking_id]:
                await connection.send_json(message)
```

**Add WebSocket endpoint:**

```python
# apps/chat/entrypoints/http/routers/chat.py

from fastapi import WebSocket, WebSocketDisconnect

manager = ConnectionManager()

@router.websocket("/ws/bookings/{booking_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    booking_id: UUID,
    current_user: User = Depends(get_current_user_ws)  # WebSocket auth
):
    """
    WebSocket endpoint for real-time chat.

    Client connects and receives messages in real-time.
    """
    # Verify user is booking participant
    await chat_service.verify_participant(booking_id, current_user.id)

    await manager.connect(websocket, booking_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Save message to database
            message = await chat_service.send_message(
                booking_id=booking_id,
                sender_id=current_user.id,
                sender_name=current_user.name,
                content=data["content"]
            )

            # Broadcast to all connected clients
            await manager.broadcast_message(
                booking_id,
                {
                    "id": str(message.id),
                    "sender_name": message.sender_name,
                    "content": message.content,
                    "created_at": message.created_at.isoformat()
                }
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket, booking_id)
```

**Client-side WebSocket:**

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/chat/ws/bookings/${bookingId}`);

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    displayMessage(message);
};

function sendMessage(content) {
    ws.send(JSON.stringify({ content }));
}
```

#### Step 2: Hybrid Approach (Backward Compatible)

Keep both polling and WebSocket endpoints:
- Modern clients use WebSocket
- Fallback to polling if WebSocket unavailable
- Gradual migration without breaking existing clients

```javascript
// Client auto-detects best transport
const chat = new ChatClient({
    bookingId,
    preferWebSocket: true,
    fallbackToPolling: true
});
```

#### Step 3: Add Redis for Multi-Instance Scaling

When running multiple FastAPI instances, use Redis pub/sub:

```python
# apps/chat/infrastructure/redis/pubsub.py

import redis.asyncio as redis

class ChatPubSub:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def publish_message(self, booking_id: UUID, message: dict):
        """Publish message to Redis channel"""
        await self.redis.publish(
            f"chat:booking:{booking_id}",
            json.dumps(message)
        )

    async def subscribe(self, booking_id: UUID):
        """Subscribe to booking chat channel"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"chat:booking:{booking_id}")
        return pubsub
```

#### Step 4: Add Push Notifications

Integrate with Firebase Cloud Messaging (FCM) or Apple Push Notification Service (APNS):

```python
# apps/chat/infrastructure/notifications/push.py

async def send_push_notification(user_id: UUID, message: Message):
    """Send push notification when user is offline"""
    user = await user_repo.get_by_id(user_id)

    if user.fcm_token and not user.is_online:
        await fcm.send(
            token=user.fcm_token,
            notification={
                "title": f"New message from {message.sender_name}",
                "body": message.content[:100]
            }
        )
```

---

## Performance Optimization

### Database Indexes

Ensure these indexes exist for query performance:

```sql
-- Critical for message retrieval
CREATE INDEX idx_messages_booking_created ON messages(booking_id, created_at);

-- Critical for unread count queries
CREATE INDEX idx_read_receipts_message_user ON message_read_receipts(message_id, user_id);

-- Optional: for sender queries
CREATE INDEX idx_messages_sender ON messages(sender_id);
```

### Query Optimization

**N+1 Query Prevention:**

Use `selectinload()` to eagerly load relationships:

```python
query = (
    select(Message)
    .options(selectinload(Message.read_receipts))  # Avoid N+1
    .where(Message.booking_id == booking_id)
)
```

**Pagination:**

Always use `skip` and `limit` to prevent loading thousands of messages:

```python
messages = await message_repo.get_by_booking(
    booking_id,
    skip=0,
    limit=50  # Load only 50 messages at a time
)
```

---

## Security Considerations

1. **Authorization**: Always verify user is booking participant before allowing access
2. **Content Validation**: Sanitize message content to prevent XSS attacks
3. **Rate Limiting**: Add rate limiting to prevent spam (e.g., max 10 messages/minute per user)
4. **Content Length**: Enforce 1000 character limit to prevent abuse
5. **SQL Injection**: SQLAlchemy ORM protects against SQL injection (never use raw SQL)

**Rate Limiting Example:**

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@router.post(
    "/bookings/{booking_id}/messages",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]  # 10 msgs/min
)
async def send_message(...):
    ...
```

---

## Monitoring & Observability

### Metrics to Track

1. **Message Volume**: Total messages sent per hour/day
2. **Active Conversations**: Number of bookings with active chat
3. **Polling Load**: Requests per second to message endpoints
4. **Read Receipt Rate**: Percentage of messages marked as read
5. **Response Time**: P95 latency for message endpoints

### Logging

```python
import logging

logger = logging.getLogger(__name__)

async def send_message(...):
    logger.info(
        "Message sent",
        extra={
            "booking_id": str(booking_id),
            "sender_id": str(sender_id),
            "message_length": len(content)
        }
    )
```

---

## Summary

This implementation plan provides a complete blueprint for building a **simple HTTP polling-based chat system** using FastAPI and SQLite. The architecture follows Clean Architecture principles with clear separation between domain, application, and infrastructure layers.

**Key Features:**
- ✅ REST-based polling (no WebSockets for MVP)
- ✅ Authorization (only booking participants)
- ✅ Read receipts and unread counts
- ✅ System notification messages
- ✅ Alembic migrations for versioning
- ✅ Comprehensive testing strategy
- ✅ Clear WebSocket upgrade path

**Implementation Time:** 4-5 hours

**Status:** BONUS/OPTIONAL - Implement after core features (booking, search, trips) are complete.

**Next Steps:**
1. Review and approve this plan
2. Create Alembic migration for chat tables
3. Implement repository layer with tests
4. Build business logic service
5. Add HTTP endpoints
6. Integrate with booking service
7. Test end-to-end with Swagger UI
8. Document API and create client examples

---

**Limitations & Future Enhancements:**

⚠️ **MVP Polling Limitations:**
- 2-5 second latency
- High server load
- No push notifications
- Requires active client

🚀 **v2 WebSocket Enhancements:**
- Real-time messaging (<100ms latency)
- Reduced server load
- Push notifications
- Typing indicators
- File attachments

---

**File Location:** `/home/darkvus/hackaton/vibe-coding-backend/.claude/docs/RF-BONUS-004-chat-simulado/fastapi.md`

**Related Plans:**
- RF-003: Booking System (dependency)
- RF-BONUS-003: Visualización Reservas (dependency)
