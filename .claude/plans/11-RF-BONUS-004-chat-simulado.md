# Plan: RF-BONUS-004 - Chat Simulado

**Issue**: #13
**Prioridad**: BAJA (Bonus - Comunicación entre viajeros)
**Estimación**: 4-5 horas
**Dependencias**:
- 04-RF-003-reserva-trayectos.md (completado)
- 10-RF-BONUS-003-visualizacion-reservas-otros.md (completado)

---

## Objetivo

Implementar un sistema de chat simulado (sin WebSockets en MVP) que permita la comunicación entre conductor y pasajeros del mismo trayecto mediante polling HTTP, facilitando coordinación y resolución de dudas.

---

## Análisis Previo

### Decisión de Arquitectura: Chat Simulado vs. Chat Real

**Chat Real (WebSockets)**
- ✅ Mensajes instantáneos en tiempo real
- ✅ Experiencia de usuario superior
- ❌ Requiere infraestructura de WebSockets
- ❌ Complejidad en deployment (Nginx, load balancing)
- ❌ Mayor costo de desarrollo (5-8 horas)

**Chat Simulado (HTTP Polling)**
- ✅ Más simple de implementar (3-4 horas)
- ✅ No requiere infraestructura adicional
- ✅ Funciona con REST API estándar
- ✅ Suficiente para MVP
- ❌ Latencia de 2-5 segundos
- ❌ Mayor carga en servidor (polling)

**Decisión**: Chat Simulado para MVP. Se puede migrar a WebSockets en v2.

### Arquitectura Objetivo

```
apps/chat/
├── domain/
│   ├── models.py                # Message, Conversation
│   └── repositories/
│       ├── message_repository.py      # IMessageRepository
│       └── conversation_repository.py # IConversationRepository
├── infrastructure/
│   ├── dependencies.py
│   ├── repositories/
│   │   ├── message_repository.py      # MessageRepository (MongoDB)
│   │   └── conversation_repository.py # ConversationRepository
│   └── services/
│       └── chat_service.py            # ChatService (business logic)
└── api/
    ├── urls.py
    └── versioning/v1/
        ├── views.py           # Endpoints de chat
        └── schemas/
            ├── requests.py    # SendMessageRequest
            └── responses.py   # MessageResponse, ConversationResponse
```

### Conceptos Clave

**1. Conversation (Conversación)**
- Agrupa mensajes de un trayecto específico
- Una conversación = un trayecto
- Participantes: conductor + pasajeros confirmados

**2. Message (Mensaje)**
- Mensaje individual de un usuario
- Asociado a una conversación
- Metadata: timestamp, leído/no leído

**3. Polling**
- Cliente consulta nuevos mensajes cada X segundos
- Endpoint: `GET /conversations/{id}/messages?since={timestamp}`
- Retorna solo mensajes nuevos

---

## Paso 1: Modelos de Dominio

**Archivo**: `apps/chat/domain/models.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class MessageType(str, Enum):
    """Tipos de mensaje"""
    TEXT = "text"
    SYSTEM = "system"  # Mensajes automáticos del sistema

class Message(BaseModel):
    """
    Entidad Message del dominio.
    Representa un mensaje en una conversación.
    """
    # Identificador
    id: Optional[str] = None

    # Relaciones
    conversation_id: str
    sender_id: str
    sender_name: str  # Desnormalizado para evitar joins

    # Contenido
    content: str = Field(..., min_length=1, max_length=1000)
    message_type: MessageType = Field(default=MessageType.TEXT)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)
    read_by: list[str] = Field(default_factory=list)  # IDs de usuarios que leyeron

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "507f1f77bcf86cd799439011",
                "sender_id": "507f1f77bcf86cd799439012",
                "sender_name": "Juan Pérez",
                "content": "¿A qué hora salimos?",
                "message_type": "text"
            }
        }

class Conversation(BaseModel):
    """
    Entidad Conversation del dominio.
    Agrupa mensajes de un trayecto.
    """
    # Identificador
    id: Optional[str] = None

    # Relación con trayecto
    trip_id: str

    # Participantes
    participant_ids: list[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    is_active: bool = Field(default=True)

    # Estadísticas
    total_messages: int = Field(default=0)

    class Config:
        json_schema_extra = {
            "example": {
                "trip_id": "507f1f77bcf86cd799439011",
                "participant_ids": [
                    "507f1f77bcf86cd799439012",
                    "507f1f77bcf86cd799439013"
                ]
            }
        }

    def is_participant(self, user_id: str) -> bool:
        """Verifica si un usuario es participante de la conversación"""
        return user_id in self.participant_ids

    def add_participant(self, user_id: str):
        """Agrega un participante a la conversación"""
        if user_id not in self.participant_ids:
            self.participant_ids.append(user_id)
```

---

## Paso 2: Repositorios - Interfaces

**Archivo**: `apps/chat/domain/repositories/message_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
from apps.chat.domain.models import Message

class IMessageRepository(ABC):
    """Contrato para repositorio de mensajes"""

    @abstractmethod
    async def create(self, message: Message) -> Message:
        """Crea un nuevo mensaje"""
        pass

    @abstractmethod
    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """Obtiene mensaje por ID"""
        pass

    @abstractmethod
    async def get_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> list[Message]:
        """
        Obtiene mensajes de una conversación.

        Args:
            since: Solo retornar mensajes después de este timestamp (para polling)
        """
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        """Marca mensaje como leído por un usuario"""
        pass

    @abstractmethod
    async def count_unread_by_user(
        self,
        conversation_id: str,
        user_id: str
    ) -> int:
        """Cuenta mensajes no leídos por un usuario"""
        pass
```

**Archivo**: `apps/chat/domain/repositories/conversation_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional
from apps.chat.domain.models import Conversation

class IConversationRepository(ABC):
    """Contrato para repositorio de conversaciones"""

    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Crea una nueva conversación"""
        pass

    @abstractmethod
    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Obtiene conversación por ID"""
        pass

    @abstractmethod
    async def get_by_trip(self, trip_id: str) -> Optional[Conversation]:
        """Obtiene conversación de un trayecto"""
        pass

    @abstractmethod
    async def get_by_participant(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Conversation]:
        """Obtiene conversaciones de un usuario"""
        pass

    @abstractmethod
    async def update(
        self,
        conversation_id: str,
        conversation: Conversation
    ) -> bool:
        """Actualiza conversación"""
        pass
```

---

## Paso 3: Implementación de Repositorios

**Archivo**: `apps/chat/infrastructure/repositories/message_repository.py`

```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional
from bson import ObjectId

from apps.chat.domain.models import Message
from apps.chat.domain.repositories.message_repository import IMessageRepository

class MessageRepository(IMessageRepository):
    """Implementación MongoDB del repositorio de mensajes"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db["messages"]

    async def create(self, message: Message) -> Message:
        """Crea mensaje en MongoDB"""
        message_dict = message.model_dump(exclude={"id"}, mode="json")
        result = await self._collection.insert_one(message_dict)
        message.id = str(result.inserted_id)
        return message

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        """Obtiene por ID"""
        try:
            doc = await self._collection.find_one({"_id": ObjectId(message_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return Message(**doc)
            return None
        except Exception:
            return None

    async def get_by_conversation(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> list[Message]:
        """Obtiene mensajes de conversación"""
        query = {"conversation_id": conversation_id}

        # Filtro para polling: solo mensajes después de timestamp
        if since:
            query["created_at"] = {"$gt": since}

        cursor = self._collection.find(query).sort("created_at", 1).skip(skip).limit(limit)

        messages = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            messages.append(Message(**doc))
        return messages

    async def mark_as_read(self, message_id: str, user_id: str) -> bool:
        """Marca como leído"""
        result = await self._collection.update_one(
            {"_id": ObjectId(message_id)},
            {"$addToSet": {"read_by": user_id}}
        )
        return result.modified_count > 0

    async def count_unread_by_user(
        self,
        conversation_id: str,
        user_id: str
    ) -> int:
        """Cuenta mensajes no leídos"""
        return await self._collection.count_documents({
            "conversation_id": conversation_id,
            "sender_id": {"$ne": user_id},  # No contar propios mensajes
            "read_by": {"$nin": [user_id]}  # No leídos por el usuario
        })
```

**Archivo**: `apps/chat/infrastructure/repositories/conversation_repository.py`

```python
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from bson import ObjectId

from apps.chat.domain.models import Conversation
from apps.chat.domain.repositories.conversation_repository import IConversationRepository

class ConversationRepository(IConversationRepository):
    """Implementación MongoDB del repositorio de conversaciones"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db["conversations"]

    async def create(self, conversation: Conversation) -> Conversation:
        """Crea conversación"""
        conversation_dict = conversation.model_dump(exclude={"id"}, mode="json")
        result = await self._collection.insert_one(conversation_dict)
        conversation.id = str(result.inserted_id)
        return conversation

    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Obtiene por ID"""
        try:
            doc = await self._collection.find_one({"_id": ObjectId(conversation_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return Conversation(**doc)
            return None
        except Exception:
            return None

    async def get_by_trip(self, trip_id: str) -> Optional[Conversation]:
        """Obtiene conversación de un trayecto"""
        doc = await self._collection.find_one({"trip_id": trip_id})
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return Conversation(**doc)
        return None

    async def get_by_participant(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[Conversation]:
        """Obtiene conversaciones del usuario"""
        cursor = self._collection.find({
            "participant_ids": user_id,
            "is_active": True
        }).sort("last_message_at", -1).skip(skip).limit(limit)

        conversations = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            conversations.append(Conversation(**doc))
        return conversations

    async def update(
        self,
        conversation_id: str,
        conversation: Conversation
    ) -> bool:
        """Actualiza conversación"""
        update_dict = conversation.model_dump(exclude={"id", "created_at"}, mode="json")
        result = await self._collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0
```

---

## Paso 4: Servicio de Chat con Lógica de Negocio

**Archivo**: `apps/chat/infrastructure/services/chat_service.py`

```python
from typing import Optional
from datetime import datetime
from fastapi import HTTPException, status

from apps.chat.domain.models import Message, Conversation, MessageType
from apps.chat.domain.repositories.message_repository import IMessageRepository
from apps.chat.domain.repositories.conversation_repository import IConversationRepository
from apps.trips.domain.repositories.trip_repository import ITripRepository
from apps.trips.domain.repositories.booking_repository import IBookingRepository

class ChatService:
    """Servicio de lógica de negocio para chat"""

    def __init__(
        self,
        message_repo: IMessageRepository,
        conversation_repo: IConversationRepository,
        trip_repo: ITripRepository,
        booking_repo: IBookingRepository
    ):
        self.message_repo = message_repo
        self.conversation_repo = conversation_repo
        self.trip_repo = trip_repo
        self.booking_repo = booking_repo

    async def get_or_create_conversation(self, trip_id: str) -> Conversation:
        """
        Obtiene conversación del trayecto o la crea si no existe.

        Participantes iniciales: conductor
        Los pasajeros se agregan al reservar
        """
        # Buscar conversación existente
        conversation = await self.conversation_repo.get_by_trip(trip_id)
        if conversation:
            return conversation

        # Crear nueva conversación
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trayecto no encontrado"
            )

        conversation = Conversation(
            trip_id=trip_id,
            participant_ids=[trip.driver_id]
        )

        return await self.conversation_repo.create(conversation)

    async def can_access_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Verifica si un usuario puede acceder a la conversación"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return False

        return conversation.is_participant(user_id)

    async def send_message(
        self,
        conversation_id: str,
        sender_id: str,
        sender_name: str,
        content: str
    ) -> Message:
        """
        Envía un mensaje a la conversación.

        Validaciones:
        - Conversación existe
        - Usuario es participante
        - Contenido no vacío
        """
        # Verificar acceso
        can_access = await self.can_access_conversation(conversation_id, sender_id)
        if not can_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta conversación"
            )

        # Crear mensaje
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content.strip()
        )

        created_message = await self.message_repo.create(message)

        # Actualizar conversación
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation:
            conversation.last_message_at = datetime.utcnow()
            conversation.total_messages += 1
            await self.conversation_repo.update(conversation_id, conversation)

        return created_message

    async def get_messages(
        self,
        conversation_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> list[Message]:
        """
        Obtiene mensajes de la conversación.

        Args:
            since: Timestamp para polling (solo mensajes después de este momento)
        """
        # Verificar acceso
        can_access = await self.can_access_conversation(conversation_id, user_id)
        if not can_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esta conversación"
            )

        return await self.message_repo.get_by_conversation(
            conversation_id, skip=skip, limit=limit, since=since
        )

    async def mark_messages_as_read(
        self,
        conversation_id: str,
        user_id: str
    ) -> int:
        """Marca todos los mensajes de la conversación como leídos"""
        messages = await self.message_repo.get_by_conversation(
            conversation_id, skip=0, limit=1000
        )

        marked_count = 0
        for message in messages:
            if message.sender_id != user_id and user_id not in message.read_by:
                await self.message_repo.mark_as_read(message.id, user_id)
                marked_count += 1

        return marked_count

    async def send_system_message(
        self,
        conversation_id: str,
        content: str
    ) -> Message:
        """
        Envía mensaje del sistema (notificación automática).

        Ejemplos:
        - "Juan Pérez se unió al viaje"
        - "El conductor ha actualizado la hora de salida"
        """
        message = Message(
            conversation_id=conversation_id,
            sender_id="system",
            sender_name="Sistema",
            content=content,
            message_type=MessageType.SYSTEM
        )

        return await self.message_repo.create(message)
```

---

## Paso 5: Integrar con BookingService

**Archivo**: `apps/trips/infrastructure/services/booking_service.py`

Actualizar para agregar pasajero a conversación y enviar mensaje de sistema:

```python
# Agregar en __init__:
from apps.chat.domain.repositories.conversation_repository import IConversationRepository
from apps.chat.infrastructure.services.chat_service import ChatService

class BookingService:
    def __init__(
        self,
        booking_repo: IBookingRepository,
        trip_repo: ITripRepository,
        conversation_repo: Optional[IConversationRepository] = None,  # NUEVO
        message_repo: Optional[IMessageRepository] = None  # NUEVO
    ):
        # ... repositorios existentes ...
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo

        # Crear chat service si están disponibles los repos
        if conversation_repo and message_repo:
            self.chat_service = ChatService(
                message_repo, conversation_repo, trip_repo, booking_repo
            )
        else:
            self.chat_service = None

    async def create_booking(self, ...):
        # ... lógica existente ...

        # NUEVO: Agregar pasajero a conversación y notificar
        if self.chat_service:
            try:
                # Obtener o crear conversación
                conversation = await self.chat_service.get_or_create_conversation(trip_id)

                # Agregar pasajero a participantes
                conversation.add_participant(passenger_id)
                await self.conversation_repo.update(conversation.id, conversation)

                # Enviar mensaje de sistema
                passenger = await self.user_repo.get_by_id(passenger_id)
                if passenger:
                    await self.chat_service.send_system_message(
                        conversation.id,
                        f"{passenger.name} se unió al viaje"
                    )
            except Exception as e:
                print(f"Error adding to conversation: {e}")

        return created_booking
```

---

## Paso 6: DTOs - Schemas

**Archivo**: `apps/chat/api/versioning/v1/schemas/requests.py`

```python
from pydantic import BaseModel, Field

class SendMessageRequest(BaseModel):
    """Request para enviar mensaje"""
    content: str = Field(..., min_length=1, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "content": "¿A qué hora salimos?"
            }
        }
```

**Archivo**: `apps/chat/api/versioning/v1/schemas/responses.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MessageResponse(BaseModel):
    """Response de mensaje"""
    id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str
    created_at: datetime
    is_read: bool

class ConversationResponse(BaseModel):
    """Response de conversación"""
    id: str
    trip_id: str
    participant_ids: list[str]
    total_messages: int
    unread_count: int
    last_message_at: Optional[datetime] = None

class ConversationWithMessagesResponse(BaseModel):
    """Response de conversación con mensajes"""
    conversation: ConversationResponse
    messages: list[MessageResponse]
```

---

## Paso 7: Endpoints

**Archivo**: `apps/chat/api/versioning/v1/views.py`

```python
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime

from apps.chat.infrastructure.services.chat_service import ChatService
from apps.chat.infrastructure.dependencies import get_chat_service
from apps.chat.api.versioning/v1.schemas.requests import SendMessageRequest
from apps.chat.api.versioning/v1.schemas.responses import (
    MessageResponse,
    ConversationResponse,
    ConversationWithMessagesResponse
)
from apps.users.infrastructure.dependencies import get_current_user
from apps.users.domain.models import User

router = APIRouter()

@router.get("/conversations", response_model=list[ConversationResponse])
async def get_my_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Listar mis conversaciones.

    **Endpoint:** `GET /chat/v1/conversations`
    """
    conversations = await chat_service.conversation_repo.get_by_participant(
        current_user.id, skip=skip, limit=limit
    )

    responses = []
    for conv in conversations:
        unread_count = await chat_service.message_repo.count_unread_by_user(
            conv.id, current_user.id
        )

        responses.append(ConversationResponse(
            id=conv.id,
            trip_id=conv.trip_id,
            participant_ids=conv.participant_ids,
            total_messages=conv.total_messages,
            unread_count=unread_count,
            last_message_at=conv.last_message_at
        ))

    return responses

@router.get("/trips/{trip_id}/conversation", response_model=ConversationWithMessagesResponse)
async def get_trip_conversation(
    trip_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
    since: Optional[datetime] = Query(None, description="Timestamp para polling")
):
    """
    Obtener conversación y mensajes de un trayecto.

    **Endpoint:** `GET /chat/v1/trips/{trip_id}/conversation?since=2025-12-15T10:00:00`

    **Polling:**
    - Cliente consulta cada 3-5 segundos con parámetro `since`
    - Solo retorna mensajes nuevos después del timestamp
    """
    # Obtener o crear conversación
    conversation = await chat_service.get_or_create_conversation(trip_id)

    # Verificar acceso
    can_access = await chat_service.can_access_conversation(
        conversation.id, current_user.id
    )
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta conversación"
        )

    # Obtener mensajes (con filtro since para polling)
    messages = await chat_service.get_messages(
        conversation.id, current_user.id, skip=0, limit=100, since=since
    )

    # Contar no leídos
    unread_count = await chat_service.message_repo.count_unread_by_user(
        conversation.id, current_user.id
    )

    return ConversationWithMessagesResponse(
        conversation=ConversationResponse(
            id=conversation.id,
            trip_id=conversation.trip_id,
            participant_ids=conversation.participant_ids,
            total_messages=conversation.total_messages,
            unread_count=unread_count,
            last_message_at=conversation.last_message_at
        ),
        messages=[MessageResponse(**m.model_dump()) for m in messages]
    )

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    Enviar mensaje a conversación.

    **Endpoint:** `POST /chat/v1/conversations/{conversation_id}/messages`
    """
    message = await chat_service.send_message(
        conversation_id,
        current_user.id,
        current_user.name,
        payload.content
    )

    return MessageResponse(**message.model_dump())

@router.post("/conversations/{conversation_id}/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_conversation_as_read(
    conversation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[ChatService, Depends(get_chat_service)]
):
    """
    Marcar todos los mensajes de una conversación como leídos.

    **Endpoint:** `POST /chat/v1/conversations/{conversation_id}/mark-read`
    """
    await chat_service.mark_messages_as_read(conversation_id, current_user.id)
    return None
```

---

## Paso 8: Dependency Injection

**Archivo**: `apps/chat/infrastructure/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.database import get_database
from apps.chat.domain.repositories.message_repository import IMessageRepository
from apps.chat.domain.repositories.conversation_repository import IConversationRepository
from apps.chat.infrastructure.repositories.message_repository import MessageRepository
from apps.chat.infrastructure.repositories.conversation_repository import ConversationRepository
from apps.chat.infrastructure.services.chat_service import ChatService
from apps.trips.infrastructure.dependencies import get_trip_repository, get_booking_repository

async def get_message_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> IMessageRepository:
    return MessageRepository(db)

async def get_conversation_repository(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)]
) -> IConversationRepository:
    return ConversationRepository(db)

async def get_chat_service(
    message_repo: Annotated[IMessageRepository, Depends(get_message_repository)],
    conversation_repo: Annotated[IConversationRepository, Depends(get_conversation_repository)],
    trip_repo: Annotated[ITripRepository, Depends(get_trip_repository)],
    booking_repo: Annotated[IBookingRepository, Depends(get_booking_repository)]
) -> ChatService:
    return ChatService(message_repo, conversation_repo, trip_repo, booking_repo)
```

---

## Paso 9: Registrar Router

**Archivo**: `apps/chat/api/urls.py`

```python
from fastapi import APIRouter
from apps.chat.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, prefix="/v1", tags=["Chat"])
```

**Actualizar**: `main.py`

```python
from apps.chat.api.urls import router as chat_router

app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
```

---

## Paso 10: Cliente JavaScript Simple (Polling)

**Archivo**: `static/chat-example.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Chat - Carpooling</title>
    <style>
        #messages { height: 400px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; }
        .message { margin: 10px 0; }
        .system { color: gray; font-style: italic; }
    </style>
</head>
<body>
    <h1>Chat del Viaje</h1>
    <div id="messages"></div>
    <input type="text" id="messageInput" placeholder="Escribe un mensaje..." />
    <button onclick="sendMessage()">Enviar</button>

    <script>
        const CONVERSATION_ID = 'your-conversation-id';
        const TOKEN = 'your-auth-token';
        let lastMessageTime = null;

        // Polling cada 3 segundos
        setInterval(fetchMessages, 3000);

        async function fetchMessages() {
            const url = lastMessageTime
                ? `/api/v1/chat/v1/conversations/${CONVERSATION_ID}?since=${lastMessageTime}`
                : `/api/v1/chat/v1/conversations/${CONVERSATION_ID}`;

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${TOKEN}` }
            });

            const data = await response.json();
            displayMessages(data.messages);

            // Actualizar timestamp para próximo polling
            if (data.messages.length > 0) {
                lastMessageTime = data.messages[data.messages.length - 1].created_at;
            }
        }

        function displayMessages(messages) {
            const container = document.getElementById('messages');
            messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `message ${msg.message_type === 'system' ? 'system' : ''}`;
                div.innerHTML = `<b>${msg.sender_name}:</b> ${msg.content}`;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const content = input.value.trim();
            if (!content) return;

            await fetch(`/api/v1/chat/v1/conversations/${CONVERSATION_ID}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${TOKEN}`
                },
                body: JSON.stringify({ content })
            });

            input.value = '';
            fetchMessages();  // Actualizar inmediatamente
        }
    </script>
</body>
</html>
```

---

## Paso 11: Crear Índices

**Archivo**: `scripts/create_indexes.py`

```python
async def create_chat_indexes():
    """Índices para chat"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    # Índice para buscar mensajes por conversación
    await db.messages.create_index([("conversation_id", 1), ("created_at", 1)])

    # Índice para buscar conversaciones por trayecto
    await db.conversations.create_index([("trip_id", 1)])

    # Índice para buscar conversaciones de un usuario
    await db.conversations.create_index([("participant_ids", 1)])

    # Índice para contar no leídos
    await db.messages.create_index([("read_by", 1)])

    print("✅ Índices de chat creados")
    client.close()
```

---

## Checklist de Implementación

- [ ] Modelos: Message, Conversation
- [ ] Interfaces: IMessageRepository, IConversationRepository
- [ ] Repositorios: MessageRepository, ConversationRepository
- [ ] ChatService con lógica de negocio
- [ ] Integración con BookingService (agregar a conversación)
- [ ] Schemas de request/response
- [ ] Endpoints:
  - [ ] GET /conversations (mis conversaciones)
  - [ ] GET /trips/{id}/conversation (conversación con polling)
  - [ ] POST /conversations/{id}/messages (enviar mensaje)
  - [ ] POST /conversations/{id}/mark-read (marcar leídos)
- [ ] Dependency injection
- [ ] Router registrado
- [ ] Índices de MongoDB
- [ ] Cliente HTML de ejemplo (opcional)
- [ ] Tests
- [ ] Documentar en Swagger

---

## Verificación

```bash
# Obtener conversación de un trayecto (con polling)
curl "http://localhost:8000/api/v1/chat/v1/trips/<TRIP_ID>/conversation" \
  -H "Authorization: Bearer <TOKEN>"

# Obtener solo mensajes nuevos (polling)
curl "http://localhost:8000/api/v1/chat/v1/trips/<TRIP_ID>/conversation?since=2025-12-15T10:00:00Z" \
  -H "Authorization: Bearer <TOKEN>"

# Enviar mensaje
curl -X POST http://localhost:8000/api/v1/chat/v1/conversations/<CONV_ID>/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"content": "¿A qué hora salimos?"}'

# Marcar como leído
curl -X POST http://localhost:8000/api/v1/chat/v1/conversations/<CONV_ID>/mark-read \
  -H "Authorization: Bearer <TOKEN>"

# Mis conversaciones
curl http://localhost:8000/api/v1/chat/v1/conversations \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Criterios de Aceptación

✅ Conversación automática por trayecto
✅ Solo participantes del viaje pueden acceder
✅ Envío de mensajes de texto
✅ Mensajes del sistema (notificaciones automáticas)
✅ Polling HTTP para obtener mensajes nuevos
✅ Marcado de mensajes como leídos
✅ Contador de mensajes no leídos
✅ Integración con sistema de reservas

---

## Limitaciones del Chat Simulado

**Limitaciones conocidas**:
- ⚠️ Latencia de 2-5 segundos (polling)
- ⚠️ Mayor carga en servidor (requests frecuentes)
- ⚠️ No hay notificaciones push
- ⚠️ Requiere cliente activo para recibir mensajes

**Migración a WebSockets (v2)**:
- FastAPI-SocketIO o python-socketio
- Redis para pub/sub entre instancias
- Notificaciones push con FCM/APNS

---

## Mejoras Futuras

- WebSockets para mensajes en tiempo real
- Indicador de "escribiendo..."
- Adjuntar imágenes/ubicación
- Mensajes de voz
- Historial ilimitado con paginación
- Notificaciones push cuando llega mensaje
- Encriptación end-to-end
- Respuestas rápidas predefinidas ("Voy en camino", "Llegué")

---

## Fin de los Planes

✅ Todos los 14 planes de acción completados:
- 00-initial-structure.md
- 01-RF-INF-001-gestion-usuarios.md
- 02-RF-001-publicacion-trayectos.md
- 03-RF-002-busqueda-trayectos.md
- 04-RF-003-reserva-trayectos.md
- 05-RF-004-listado-reservas.md
- 06-RF-005-visualizacion-mapas.md
- 07-RF-006-matching-avanzado.md
- 08-RF-BONUS-001-matching-aproximado-geografico.md
- 09-RF-BONUS-002-estimacion-co2-evitado.md
- 10-RF-BONUS-003-visualizacion-reservas-otros.md
- 11-RF-BONUS-004-chat-simulado.md

**Próximo paso**: Implementar cada plan siguiendo el orden de dependencias.
