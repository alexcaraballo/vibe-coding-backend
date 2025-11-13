# Documentación API - Vibe Coding Carpooling

## 📋 Información General

**Versión:** v0.1.0
**Base URL:** `http://localhost:8001/api/v1`
**Formato:** JSON
**Autenticación:** JWT (Bearer Token)

## 🔐 Autenticación

La API utiliza JWT (JSON Web Tokens) para autenticación. La mayoría de los endpoints requieren incluir el token en el header `Authorization`.

```http
Authorization: Bearer <tu_token_jwt>
```

---

## 📚 Índice de Endpoints

### 👤 Autenticación y Usuarios
- [POST /auth/register](#post-authregister) - Registrar usuario
- [POST /auth/login](#post-authlogin) - Iniciar sesión
- [GET /users/me](#get-usersme) - Obtener perfil actual
- [PUT /users/me](#put-usersme) - Actualizar perfil
- [GET /users/{user_id}](#get-usersuser_id) - Obtener perfil público

### 🚗 Gestión de Trayectos
- [POST /trips/](#post-trips) - Crear trayecto
- [GET /trips/search](#get-tripssearch) - Buscar trayectos
- [GET /trips/{trip_id}](#get-tripstrip_id) - Obtener trayecto
- [GET /trips/](#get-trips) - Listar trayectos
- [GET /trips/driver/{driver_id}](#get-tripsdriverdriver_id) - Trayectos por conductor
- [PUT /trips/{trip_id}](#put-tripstrip_id) - Actualizar trayecto
- [DELETE /trips/{trip_id}](#delete-tripstrip_id) - Cancelar trayecto

### 📅 Gestión de Reservas
- [POST /trips/{trip_id}/book](#post-tripstrip_idbook) - Reservar plaza
- [GET /trips/bookings/my](#get-tripsbookingsmy) - Mis reservas
- [GET /trips/bookings/{booking_id}](#get-tripsbookingsbooking_id) - Detalle de reserva
- [DELETE /trips/bookings/{booking_id}](#delete-tripsbookingsbooking_id) - Cancelar reserva
- [GET /trips/{trip_id}/bookings](#get-tripstrip_idbookings) - Reservas de trayecto (conductor)

### 💬 Chat Conductor-Pasajero (RF-BONUS-004)
- [POST /trips/bookings/{booking_id}/chat](#post-tripsbookingsbooking_idchat) - Enviar mensaje
- [GET /trips/bookings/{booking_id}/chat](#get-tripsbookingsbooking_idchat) - Obtener conversación
- [DELETE /trips/chat/{message_id}](#delete-tripschatmessage_id) - Eliminar mensaje

### 🗺️ Visualización y Mapas
- [GET /trips/{trip_id}/bookings/public](#get-tripstrip_idbookingspublic) - Vista pública de reservas
- [GET /trips/{trip_id}/route-with-stops](#get-tripstrip_idroute-with-stops) - Ruta con paradas

### 🔍 Matching y Búsqueda Avanzada
- [POST /matching/travel-request](#post-matchingtravel-request) - Crear solicitud de viaje
- [GET /matching/matches/{request_id}](#get-matchingmatchesrequest_id) - Obtener matches
- [GET /matching/my-requests](#get-matchingmy-requests) - Mis solicitudes

### 🌱 Impacto Ambiental (CO₂)
- [GET /trips/{trip_id}/co2-impact](#get-tripstrip_idco2-impact) - Impacto CO₂ del trayecto
- [GET /trips/users/me/co2-stats](#get-tripsusersmeco2-stats) - Estadísticas de CO₂

---

## 🔐 Endpoints de Autenticación

### POST /auth/register

Registra un nuevo usuario en el sistema.

**Autenticación:** No requerida

**Request Body:**
```json
{
  "email": "usuario@example.com",
  "password": "SecurePass123!",
  "name": "Juan Pérez",
  "role": "driver",  // "driver", "passenger", o "both"
  "phone": "+34600000000"
}
```

**Response 201 Created:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "usuario@example.com",
    "name": "Juan Pérez",
    "phone": "+34600000000",
    "role": "driver",
    "is_active": true,
    "is_verified": false,
    "created_at": "2025-11-13T10:00:00"
  }
}
```

**Errores:**
- `400 Bad Request` - Email ya existe o datos inválidos
- `422 Unprocessable Entity` - Formato de datos incorrecto

---

### POST /auth/login

Inicia sesión con credenciales existentes.

**Autenticación:** No requerida

**Request Body (form-data):**
```
username: usuario@example.com
password: SecurePass123!
```

**Response 200 OK:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errores:**
- `401 Unauthorized` - Credenciales incorrectas
- `422 Unprocessable Entity` - Formato incorrecto

---

### GET /users/me

Obtiene el perfil del usuario autenticado.

**Autenticación:** Requerida

**Response 200 OK:**
```json
{
  "id": 1,
  "email": "usuario@example.com",
  "name": "Juan Pérez",
  "phone": "+34600000000",
  "role": "driver",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-11-13T10:00:00",
  "vehicle_model": "Toyota Prius",
  "vehicle_plate": "1234ABC",
  "license_number": "12345678A"
}
```

---

### PUT /users/me

Actualiza el perfil del usuario autenticado.

**Autenticación:** Requerida

**Request Body (campos opcionales):**
```json
{
  "name": "Juan Pérez García",
  "phone": "+34611222333",
  "vehicle_model": "Toyota Prius 2020",
  "vehicle_plate": "5678XYZ",
  "license_number": "87654321B"
}
```

**Response 200 OK:** Usuario actualizado

---

### GET /users/{user_id}

Obtiene el perfil público de un usuario.

**Autenticación:** No requerida

**Response 200 OK:**
```json
{
  "id": 1,
  "name": "Juan Pérez",
  "role": "driver",
  "created_at": "2025-11-13T10:00:00"
}
```

---

## 🚗 Endpoints de Trayectos

### POST /trips/

Crea un nuevo trayecto como conductor.

**Autenticación:** Requerida (rol: driver o both)

**Request Body:**
```json
{
  "origin": "Cádiz",
  "destination": "Sevilla",
  "departure_date": "2025-12-20",
  "departure_time": "10:00:00",
  "available_seats": 3,
  "price_per_seat": 8.0,
  "description": "Viaje tranquilo, acepto mascotas",
  "max_detour_minutes": 30,
  "vehicle_type": "gasoline",  // "gasoline", "diesel", "hybrid", "electric"
  "origin_lat": 36.5297,
  "origin_lng": -6.2926,
  "destination_lat": 37.3891,
  "destination_lng": -5.9845
}
```

**Response 201 Created:**
```json
{
  "id": 1,
  "origin": "Cádiz",
  "destination": "Sevilla",
  "departure_date": "2025-12-20",
  "departure_time": "10:00:00",
  "available_seats": 3,
  "total_seats": 3,
  "driver_id": 1,
  "status": "active",
  "origin_lat": 36.5297,
  "origin_lng": -6.2926,
  "destination_lat": 37.3891,
  "destination_lng": -5.9845,
  "vehicle_type": "gasoline",
  "distance_km": 121.7,
  "co2_saved_per_passenger_kg": 14.604,
  "total_co2_saved_kg": 0.0,
  "price_per_seat": 8.0,
  "description": "Viaje tranquilo, acepto mascotas",
  "created_at": "2025-11-13T10:00:00"
}
```

**Errores:**
- `400 Bad Request` - Fecha pasada o datos inválidos
- `403 Forbidden` - Usuario no es conductor

---

### GET /trips/search

Busca trayectos disponibles con filtros.

**Autenticación:** No requerida

**Query Parameters:**
- `origin` (opcional) - Ciudad de origen (búsqueda parcial, case-insensitive)
- `destination` (opcional) - Ciudad de destino (búsqueda parcial, case-insensitive)
- `date_from` (opcional) - Fecha mínima (formato: YYYY-MM-DD, por defecto: hoy)
- `skip` (opcional) - Número de registros a saltar (default: 0)
- `limit` (opcional) - Número máximo de registros (default: 100, max: 500)

**Ejemplo:**
```
GET /trips/search?origin=cadiz&destination=sev&date_from=2025-12-15
```

**Response 200 OK:**
```json
{
  "trips": [
    {
      "id": 1,
      "origin": "Cádiz",
      "destination": "Sevilla",
      "departure_date": "2025-12-20",
      "departure_time": "10:00:00",
      "available_seats": 3,
      "driver_id": 1,
      "price_per_seat": 8.0,
      "distance_km": 121.7,
      "co2_saved_per_passenger_kg": 14.604
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

---

### GET /trips/{trip_id}

Obtiene detalles de un trayecto específico.

**Autenticación:** No requerida

**Response 200 OK:** Objeto Trip completo

**Errores:**
- `404 Not Found` - Trayecto no existe

---

### GET /trips/

Lista todos los trayectos con paginación.

**Autenticación:** No requerida

**Query Parameters:**
- `skip` (opcional) - Registros a saltar
- `limit` (opcional) - Máximo de registros
- `status` (opcional) - Filtrar por estado (active, completed, cancelled)

**Response 200 OK:** Lista de trayectos con paginación

---

### GET /trips/driver/{driver_id}

Lista trayectos de un conductor específico.

**Autenticación:** No requerida

**Response 200 OK:** Lista de trayectos del conductor

---

### PUT /trips/{trip_id}

Actualiza un trayecto existente.

**Autenticación:** Requerida (solo el conductor propietario)

**Request Body (campos opcionales):**
```json
{
  "available_seats": 2,
  "price_per_seat": 10.0,
  "description": "Actualización: salida a las 09:15",
  "status": "active",
  "max_detour_minutes": 45
}
```

**Response 200 OK:** Trayecto actualizado

**Errores:**
- `403 Forbidden` - No eres el conductor de este trayecto
- `404 Not Found` - Trayecto no existe

---

### DELETE /trips/{trip_id}

Cancela un trayecto (soft delete).

**Autenticación:** Requerida (solo el conductor propietario)

**Response 204 No Content:** Trayecto cancelado

---

## 📅 Endpoints de Reservas

### POST /trips/{trip_id}/book

Reserva plazas en un trayecto.

**Autenticación:** Requerida

**Request Body:**
```json
{
  "seats_requested": 1,
  "passenger_notes": "Llegaré 5 minutos antes",
  "pickup_location": "Estación de tren de Cádiz",
  "dropoff_location": "Plaza de España, Sevilla",
  "pickup_lat": 36.5297,
  "pickup_lng": -6.2926,
  "dropoff_lat": 37.3891,
  "dropoff_lng": -5.9845
}
```

**Response 201 Created:**
```json
{
  "id": 1,
  "trip_id": 1,
  "passenger_id": 2,
  "seats_booked": 1,
  "status": "confirmed",
  "pickup_location": "Estación de tren de Cádiz",
  "dropoff_location": "Plaza de España, Sevilla",
  "passenger_notes": "Llegaré 5 minutos antes",
  "booking_date": "2025-11-13T10:00:00",
  "is_active": true
}
```

**Errores:**
- `400 Bad Request` - No hay plazas disponibles o reserva duplicada
- `403 Forbidden` - No puedes reservar tu propio trayecto
- `404 Not Found` - Trayecto no existe

---

### GET /trips/bookings/my

Lista todas las reservas del usuario autenticado.

**Autenticación:** Requerida

**Query Parameters:**
- `status` (opcional) - Filtrar por estado
- `skip`, `limit` - Paginación

**Response 200 OK:**
```json
[
  {
    "booking": {
      "id": 1,
      "trip_id": 1,
      "seats_booked": 1,
      "status": "confirmed"
    },
    "trip": {
      "id": 1,
      "origin": "Cádiz",
      "destination": "Sevilla",
      "departure_date": "2025-12-20"
    },
    "driver": {
      "id": 3,
      "name": "Ana Conductora"
    }
  }
]
```

---

### GET /trips/bookings/{booking_id}

Obtiene detalles de una reserva específica.

**Autenticación:** Requerida (pasajero o conductor)

**Response 200 OK:** Detalle completo de la reserva con información del trayecto

---

### DELETE /trips/bookings/{booking_id}

Cancela una reserva.

**Autenticación:** Requerida (solo el pasajero propietario)

**Response 204 No Content:** Reserva cancelada

---

### GET /trips/{trip_id}/bookings

Lista todas las reservas de un trayecto (solo conductor).

**Autenticación:** Requerida (conductor del trayecto)

**Response 200 OK:** Lista de reservas del trayecto

---

## 💬 Endpoints de Chat (RF-BONUS-004)

### POST /trips/bookings/{booking_id}/chat

Envía un mensaje de chat en una reserva.

**Autenticación:** Requerida (conductor o pasajero de la reserva)

**Request Body:**
```json
{
  "message": "Hola, ¿a qué hora pasas a recogerme?"
}
```

**Response 201 Created:**
```json
{
  "id": 1,
  "booking_id": 5,
  "sender_id": 2,
  "message": "Hola, ¿a qué hora pasas a recogerme?",
  "sent_at": "2025-11-13T14:30:00",
  "is_read": false,
  "read_at": null
}
```

**Características:**
- Solo el conductor y el pasajero de la reserva pueden enviar mensajes
- Los mensajes son privados y solo visibles para ambas partes
- El mensaje se valida (1-1000 caracteres)

**Errores:**
- `400 Bad Request` - Mensaje vacío o muy largo
- `403 Forbidden` - No tienes permiso para enviar mensajes en este chat
- `404 Not Found` - Reserva no existe

---

### GET /trips/bookings/{booking_id}/chat

Obtiene la conversación completa de una reserva.

**Autenticación:** Requerida (conductor o pasajero de la reserva)

**Query Parameters:**
- `skip` (opcional) - Mensajes a saltar (default: 0)
- `limit` (opcional) - Máximo de mensajes (default: 100, max: 500)

**Response 200 OK:**
```json
{
  "booking_id": 5,
  "messages": [
    {
      "id": 1,
      "booking_id": 5,
      "sender_id": 2,
      "message": "Hola, ¿a qué hora pasas a recogerme?",
      "sent_at": "2025-11-13T14:30:00",
      "is_read": true,
      "read_at": "2025-11-13T14:35:00"
    },
    {
      "id": 2,
      "booking_id": 5,
      "sender_id": 1,
      "message": "Hola! Paso a las 10:00 AM exactamente. Te envío un mensaje cuando esté cerca.",
      "sent_at": "2025-11-13T14:35:00",
      "is_read": false,
      "read_at": null
    }
  ],
  "total_messages": 2,
  "unread_count": 1
}
```

**Características:**
- Mensajes ordenados cronológicamente (más antiguos primero)
- Los mensajes se marcan automáticamente como leídos al obtenerlos
- `unread_count` muestra mensajes no leídos del otro usuario
- Los mensajes eliminados no aparecen en la conversación

**Errores:**
- `403 Forbidden` - No tienes permiso para ver este chat
- `404 Not Found` - Reserva no existe

---

### DELETE /trips/chat/{message_id}

Elimina un mensaje de chat (soft delete).

**Autenticación:** Requerida (solo el remitente del mensaje)

**Response 204 No Content:** Mensaje eliminado

**Características:**
- Solo puedes eliminar tus propios mensajes
- El mensaje se marca como eliminado pero se preserva en la base de datos
- Los mensajes eliminados no aparecen en las conversaciones

**Errores:**
- `403 Forbidden` - Solo puedes eliminar tus propios mensajes
- `404 Not Found` - Mensaje no existe

---

## 🗺️ Endpoints de Visualización

### GET /trips/{trip_id}/bookings/public

Obtiene visualización pública de reservas (datos anonimizados).

**Autenticación:** No requerida

**Response 200 OK:**
```json
{
  "trip": {
    "id": 1,
    "origin": "Cádiz",
    "destination": "Sevilla",
    "departure_date": "2025-12-20",
    "available_seats": 1,
    "total_seats": 3
  },
  "total_bookings": 2,
  "total_seats_booked": 2,
  "bookings": [
    {
      "booking_id": 1,
      "seats_booked": 1,
      "pickup_location": "Estación de Jerez",
      "dropoff_location": "Plaza de España, Sevilla",
      "pickup_lat": 36.6868,
      "pickup_lng": -6.1362,
      "dropoff_lat": 37.3772,
      "dropoff_lng": -5.9869,
      "booking_date": "2025-11-13T10:00:00"
    }
  ]
}
```

**Características:**
- No expone nombres ni IDs de pasajeros
- Muestra ubicaciones de recogida/bajada con coordenadas
- Útil para visualización en mapas

---

### GET /trips/{trip_id}/route-with-stops

Obtiene ruta completa con todas las paradas para visualización en mapa.

**Autenticación:** No requerida

**Response 200 OK:**
```json
{
  "trip_id": 1,
  "origin": "Cádiz",
  "destination": "Sevilla",
  "total_distance_km": 121.7,
  "waypoints": [
    {
      "type": "origin",
      "location": "Cádiz",
      "lat": 36.5297,
      "lng": -6.2926,
      "order": 0
    },
    {
      "type": "pickup",
      "location": "Estación de Jerez",
      "lat": 36.6868,
      "lng": -6.1362,
      "booking_id": 1,
      "order": 1
    },
    {
      "type": "dropoff",
      "location": "Plaza de España, Sevilla",
      "lat": 37.3772,
      "lng": -5.9869,
      "booking_id": 1,
      "order": 2
    },
    {
      "type": "destination",
      "location": "Sevilla",
      "lat": 37.3891,
      "lng": -5.9845,
      "order": 3
    }
  ]
}
```

**Tipos de waypoints:**
- `origin` - Punto de origen del trayecto
- `destination` - Punto de destino del trayecto
- `pickup` - Punto de recogida de pasajero
- `dropoff` - Punto de bajada de pasajero

---

## 🔍 Endpoints de Matching

### POST /matching/travel-request

Crea una solicitud de viaje para matching automático.

**Autenticación:** Requerida

**Request Body:**
```json
{
  "origin": "Cádiz",
  "destination": "Sevilla",
  "desired_date": "2025-12-20",
  "seats_needed": 1,
  "max_price": 10.0,
  "flexible_dates": true,
  "flexibility_days": 2,
  "origin_lat": 36.5297,
  "origin_lng": -6.2926,
  "destination_lat": 37.3891,
  "destination_lng": -5.9845
}
```

**Response 201 Created:**
```json
{
  "id": 1,
  "user_id": 2,
  "origin": "Cádiz",
  "destination": "Sevilla",
  "desired_date": "2025-12-20",
  "seats_needed": 1,
  "max_price": 10.0,
  "status": "active",
  "created_at": "2025-11-13T10:00:00"
}
```

---

### GET /matching/matches/{request_id}

Obtiene trayectos que coinciden con una solicitud de viaje.

**Autenticación:** Requerida (propietario de la solicitud)

**Query Parameters:**
- `max_distance_km` (opcional) - Distancia máxima del desvío (default: 10)
- `skip`, `limit` - Paginación

**Response 200 OK:**
```json
{
  "request": {
    "id": 1,
    "origin": "Cádiz",
    "destination": "Sevilla"
  },
  "matches": [
    {
      "trip": {
        "id": 1,
        "origin": "Cádiz",
        "destination": "Sevilla",
        "departure_date": "2025-12-20",
        "available_seats": 3
      },
      "compatibility_score": 0.95,
      "detour_distance_km": 2.5,
      "detour_time_minutes": 5,
      "match_type": "exact",
      "pickup_point": {
        "lat": 36.5297,
        "lng": -6.2926,
        "distance_from_request_origin_km": 0.5
      },
      "dropoff_point": {
        "lat": 37.3891,
        "lng": -5.9845,
        "distance_from_request_destination_km": 0.3
      }
    }
  ],
  "total_matches": 1
}
```

**Tipos de match:**
- `exact` - Origen y destino exactos
- `origin_match` - Solo origen coincide
- `destination_match` - Solo destino coincide
- `nearby` - Cercano geográficamente

---

### GET /matching/my-requests

Lista las solicitudes de viaje del usuario autenticado.

**Autenticación:** Requerida

**Response 200 OK:** Lista de solicitudes propias

---

## 🌱 Endpoints de Impacto Ambiental

### GET /trips/{trip_id}/co2-impact

Obtiene el impacto de CO₂ evitado por un trayecto.

**Autenticación:** No requerida

**Response 200 OK:**
```json
{
  "trip_id": 1,
  "vehicle_type": "gasoline",
  "distance_km": 121.7,
  "co2_saved_per_passenger_kg": 14.604,
  "total_co2_saved_kg": 29.208,
  "passengers_count": 2,
  "equivalences": {
    "trees": "Equivalente a plantar 11.7 árboles por un año",
    "km": "Equivalente a no conducir 146.0 km en coche convencional"
  }
}
```

**Factores de emisión por tipo de vehículo:**
- Gasoline: 120 g CO₂/km
- Diesel: 105 g CO₂/km
- Hybrid: 70 g CO₂/km
- Electric: 0 g CO₂/km

---

### GET /trips/users/me/co2-stats

Obtiene estadísticas de CO₂ del usuario autenticado.

**Autenticación:** Requerida

**Response 200 OK:**
```json
{
  "user_id": 1,
  "total_co2_saved_kg": 156.80,
  "trips_as_driver": 5,
  "trips_as_passenger": 3,
  "total_trips": 8,
  "average_co2_per_trip_kg": 19.60,
  "equivalence_trees": 62.7,
  "equivalence_km_not_driven": 784.0,
  "description": {
    "trees": "Equivalente a plantar 62.7 árboles por un año",
    "km": "Equivalente a no conducir 784.0 km en coche convencional"
  }
}
```

---

## 📊 Modelos de Datos

### User
```typescript
{
  id: number
  email: string
  name: string
  phone: string
  role: "driver" | "passenger" | "both"
  is_active: boolean
  is_verified: boolean
  created_at: datetime
  vehicle_model?: string
  vehicle_plate?: string
  license_number?: string
}
```

### Trip
```typescript
{
  id: number
  origin: string
  destination: string
  departure_date: date
  departure_time: time
  available_seats: number
  total_seats: number
  driver_id: number
  status: "active" | "completed" | "cancelled"
  origin_lat?: number
  origin_lng?: number
  destination_lat?: number
  destination_lng?: number
  vehicle_type: "gasoline" | "diesel" | "hybrid" | "electric"
  distance_km?: number
  co2_saved_per_passenger_kg?: number
  total_co2_saved_kg?: number
  price_per_seat?: number
  description?: string
  max_detour_minutes: number
  created_at: datetime
}
```

### Booking
```typescript
{
  id: number
  trip_id: number
  passenger_id: number
  seats_booked: number
  status: "pending" | "confirmed" | "cancelled" | "completed"
  pickup_location?: string
  dropoff_location?: string
  pickup_lat?: number
  pickup_lng?: number
  dropoff_lat?: number
  dropoff_lng?: number
  passenger_notes?: string
  booking_date: datetime
  is_active: boolean
}
```

### ChatMessage
```typescript
{
  id: number
  booking_id: number
  sender_id: number
  message: string
  sent_at: datetime
  is_read: boolean
  read_at?: datetime
  is_deleted: boolean
}
```

### TravelRequest
```typescript
{
  id: number
  user_id: number
  origin: string
  destination: string
  desired_date: date
  seats_needed: number
  max_price?: number
  flexible_dates: boolean
  flexibility_days?: number
  origin_lat?: number
  origin_lng?: number
  destination_lat?: number
  destination_lng?: number
  status: "active" | "matched" | "cancelled"
  created_at: datetime
}
```

---

## ⚠️ Códigos de Estado HTTP

| Código | Descripción |
|--------|-------------|
| 200 | OK - Solicitud exitosa |
| 201 | Created - Recurso creado exitosamente |
| 204 | No Content - Solicitud exitosa sin contenido |
| 400 | Bad Request - Datos inválidos o reglas de negocio violadas |
| 401 | Unauthorized - Token inválido o ausente |
| 403 | Forbidden - Sin permisos para acceder al recurso |
| 404 | Not Found - Recurso no encontrado |
| 422 | Unprocessable Entity - Formato de datos incorrecto |
| 500 | Internal Server Error - Error del servidor |

---

## 🛡️ Reglas de Negocio

### Trayectos
- Solo usuarios con rol `driver` o `both` pueden crear trayectos
- La fecha del trayecto debe ser futura
- `available_seats` debe ser entre 1 y 10
- El conductor no puede reservar su propio trayecto

### Reservas
- `seats_requested` debe ser ≤ `available_seats`
- No se permiten reservas duplicadas del mismo pasajero
- Solo el pasajero propietario puede cancelar su reserva
- Al reservar, las plazas disponibles se decrementan automáticamente
- Al cancelar, las plazas se liberan automáticamente

### Chat
- Solo el conductor y el pasajero de una reserva pueden acceder al chat
- Los mensajes son privados y solo visibles para ambas partes
- Los mensajes deben tener entre 1 y 1000 caracteres
- Los mensajes se marcan como leídos automáticamente al obtener la conversación
- Solo el remitente puede eliminar sus propios mensajes
- Los mensajes eliminados se marcan como `is_deleted=true` (soft delete)

### Matching
- El sistema busca trayectos compatibles considerando:
  - Fechas cercanas (si `flexible_dates = true`)
  - Ubicaciones geográficamente cercanas
  - Plazas suficientes disponibles
  - Precio dentro del rango especificado
- Se calcula un `compatibility_score` de 0 a 1

### CO₂
- El cálculo se basa en la distancia real (OSRM) o haversine × 1.3
- Se usa el factor de emisión según tipo de vehículo
- CO₂ evitado = distancia × factor × pasajeros
- Las estadísticas incluyen viajes como conductor y pasajero

---

## 🔧 Ejemplos de Uso

### Flujo Completo: Registro → Búsqueda → Reserva → Chat

```bash
# 1. Registrar como pasajero
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "maria@example.com",
    "password": "SecurePass123!",
    "name": "María García",
    "role": "passenger",
    "phone": "+34600111222"
  }'

# Respuesta: { "access_token": "...", "user": {...} }

# 2. Buscar trayectos
curl "http://localhost:8001/api/v1/trips/search?origin=cadiz&destination=sevilla"

# 3. Reservar trayecto
curl -X POST http://localhost:8001/api/v1/trips/1/book \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "seats_requested": 1,
    "passenger_notes": "Estaré en la estación a las 9:50",
    "pickup_location": "Estación de Cádiz",
    "pickup_lat": 36.5297,
    "pickup_lng": -6.2926
  }'

# 4. Enviar mensaje al conductor
curl -X POST http://localhost:8001/api/v1/trips/bookings/1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "message": "Hola, ¿a qué hora pasas a recogerme?"
  }'

# 5. Leer conversación
curl http://localhost:8001/api/v1/trips/bookings/1/chat \
  -H "Authorization: Bearer <token>"

# 6. Ver mis reservas
curl http://localhost:8001/api/v1/trips/bookings/my \
  -H "Authorization: Bearer <token>"
```

---

## 📝 Notas Adicionales

### Paginación
Todos los endpoints de lista soportan paginación mediante `skip` y `limit`:
```
GET /trips/?skip=0&limit=20
```

### Búsqueda Case-Insensitive
Los endpoints de búsqueda (search, matching) son case-insensitive y permiten búsqueda parcial:
- "cadiz" encuentra "Cádiz"
- "sev" encuentra "Sevilla"

### Timestamps
Todos los timestamps están en formato ISO 8601 UTC:
```
2025-11-13T10:00:00
```

### Coordinadas Geográficas
- Latitud: -90 a 90
- Longitud: -180 a 180
- Formato decimal (ej: 36.5297, -6.2926)

### Chat en Tiempo Real
- El chat es simulado (no WebSockets en esta versión)
- Los clientes deben hacer polling al endpoint GET para obtener nuevos mensajes
- Los mensajes se marcan como leídos automáticamente al recuperar la conversación
- Se proporciona `unread_count` para mostrar notificaciones

---

## 🚀 Testing

Para probar la API, scripts de test están disponibles en `/tmp/`:
- `test_rf_bonus_002_co2.sh` - Tests de CO₂
- `test_rf_bonus_003_public_booking_viz.sh` - Tests de visualización pública
- `test_rf_bonus_004_chat.sh` - Tests de chat conductor-pasajero
- `test_rf006_matching.sh` - Tests de matching

Ejecutar un test:
```bash
bash /tmp/test_rf_bonus_004_chat.sh
```

---

## 📞 Soporte

Para reportar issues o contribuir:
- GitHub: [vibe-coding-backend](https://github.com/vibe-coding/backend)
- Email: soporte@vibecoding.com

---

**Última actualización:** 2025-11-13
**Versión:** v0.1.0
**Features implementados:** 11/11 (RF-INF-001 + RF-001 a RF-006 + RF-BONUS-001 a RF-BONUS-004)
