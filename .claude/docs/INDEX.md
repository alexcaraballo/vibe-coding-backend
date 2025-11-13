# FastAPI Implementation Plans - Index

## Overview

Este directorio contiene los planes de implementación FastAPI completos para todos los requisitos funcionales del sistema de carpooling. Cada plan está adaptado para **SQLite3 + SQLAlchemy async** siguiendo **Clean Architecture** (arquitectura hexagonal).

## 📋 Plans Generated

### ✅ Core Infrastructure

| Plan | Description | Status | Estimated Time | Dependencies |
|------|-------------|--------|----------------|--------------|
| [Initial Structure](./initial-structure/fastapi.md) | Estructura base del proyecto con SQLite3 + SQLAlchemy | ✅ **IMPLEMENTED** | N/A | None |

### 🔐 Authentication & User Management

| Plan | Description | Status | Estimated Time | Dependencies |
|------|-------------|--------|----------------|--------------|
| [RF-INF-001: Gestión de Usuarios](./RF-INF-001-gestion-usuarios/fastapi.md) | Registro, login JWT, perfiles, roles (driver/passenger) | 📋 Ready | 6-8 hours | Initial Structure |

**Key Features:**
- User registration with email/password
- JWT authentication with bcrypt password hashing
- User profiles with driver/passenger roles
- SQLAlchemy User model with async repository
- OAuth2 password flow for login

---

### 🚗 Trip Management

| Plan | Description | Status | Estimated Time | Dependencies |
|------|-------------|--------|----------------|--------------|
| [RF-001: Publicación de Trayectos](./RF-001-publicacion-trayectos/fastapi.md) | Conductores publican trayectos disponibles | 📋 Ready | 6-8 hours | RF-INF-001 |
| [RF-002: Búsqueda de Trayectos](./RF-002-busqueda-trayectos/fastapi.md) | Búsqueda con filtros (origen, destino, fecha) | 📋 Ready | 2-3 hours | RF-001 |
| [RF-003: Reserva de Trayectos](./RF-003-reserva-trayectos/fastapi.md) | Pasajeros reservan plazas con validación de disponibilidad | 📋 Ready | 14-16 hours | RF-001, RF-INF-001 |
| [RF-004: Listado de Reservas](./RF-004-listado-reservas/fastapi.md) | Usuarios ven sus reservas (pasajero) y reservas de sus trayectos (conductor) | 📋 Ready | 11-14 hours | RF-003 |

**Key Features:**
- Trip entity with driver relationship
- Search with SQLAlchemy filters and indexes
- Booking with concurrency control (SELECT FOR UPDATE)
- Transaction management for seat consistency
- Eager loading to prevent N+1 queries

---

### 🎯 Matching Engine

| Plan | Description | Status | Estimated Time | Dependencies |
|------|-------------|--------|----------------|--------------|
| [RF-006: Matching Avanzado](./RF-006-matching-avanzado/fastapi.md) | Motor de matching con scoring de compatibilidad | 📋 Ready | 8-10 hours | RF-001, RF-002 |

**Key Features:**
- Geographic compatibility with Haversine formula
- Detour constraint enforcement
- Weighted compatibility scoring (60% proximity + 40% time)
- TravelRequest entity for storing passenger searches
- Accept match operation (creates booking + updates roadmap)

---

### 🗺️ Maps Integration

| Plan | Description | Status | Estimated Time | Dependencies |
|------|-------------|--------|----------------|--------------|
| [RF-005: Visualización de Mapas](./RF-005-visualizacion-mapas/fastapi.md) | Integración con servicios de mapas (OSM, Mapbox, Google) | 📋 Ready | 11-14 hours | RF-001 |

**Key Features:**
- Map service abstraction (OpenStreetMap, Mapbox, Google Maps)
- Geocoding API (address → lat/lng)
- Route calculation API
- SQLite-based caching for geocoding results
- Error handling with retry logic and rate limiting

---

### ⭐ Bonus Features

| Plan | Description | Status | Estimated Time | Dependencies |
|------|-------------|--------|----------------|--------------|
| [RF-BONUS-001: Matching Geográfico](./RF-BONUS-001-matching-aproximado-geografico/fastapi.md) | Matching mejorado con cálculos geográficos precisos | 📋 Ready (BONUS) | 3-4 hours | RF-006 |
| [RF-BONUS-002: Estimación CO2](./RF-BONUS-002-estimacion-co2-evitado/fastapi.md) | Cálculo de emisiones CO2 evitadas por carpooling | 📋 Ready (BONUS) | 5-7 hours | RF-001, RF-003 |
| [RF-BONUS-003: Visualización Pasajeros](./RF-BONUS-003-visualizacion-reservas-otros/fastapi.md) | Ver pasajeros confirmados en un trayecto con privacidad | 📋 Ready (BONUS) | 3-4 hours | RF-004 |
| [RF-BONUS-004: Chat Simulado](./RF-BONUS-004-chat-simulado/fastapi.md) | Mensajería REST entre conductores y pasajeros | 📋 Ready (BONUS) | 4-5 hours | RF-003 |

**Key Features:**
- **BONUS-001**: Perpendicular distance calculations, SQLite custom functions
- **BONUS-002**: CO2Calculator service, vehicle emission factors, environmental equivalences
- **BONUS-003**: Privacy-respecting passenger visibility with user-controlled settings
- **BONUS-004**: HTTP polling-based chat, WebSocket upgrade path documented

---

## 🏗️ Implementation Order

### Phase 1: Foundation (CRITICAL PATH)
1. ✅ **Initial Structure** (Already implemented)
2. 📋 **RF-INF-001: Gestión de Usuarios** - Base authentication system

### Phase 2: Core Trip Functionality
3. 📋 **RF-001: Publicación de Trayectos** - Drivers publish trips
4. 📋 **RF-002: Búsqueda de Trayectos** - Search trips with filters

### Phase 3: Bookings
5. 📋 **RF-003: Reserva de Trayectos** - Passengers book seats (COMPLEX: 14-16h)
6. 📋 **RF-004: Listado de Reservas** - View bookings

### Phase 4: Advanced Features
7. 📋 **RF-006: Matching Avanzado** - Matching engine
8. 📋 **RF-005: Visualización de Mapas** - Maps integration

### Phase 5: Bonus Features (Optional)
9. ⭐ **RF-BONUS-001**: Enhanced geographic matching
10. ⭐ **RF-BONUS-002**: CO2 impact tracking
11. ⭐ **RF-BONUS-003**: Passenger visibility
12. ⭐ **RF-BONUS-004**: In-app messaging

---

## 📊 Total Estimated Time

- **Core Features**: 48-62 hours
- **Bonus Features**: 15-20 hours
- **Total**: 63-82 hours

---

## 🔧 Technology Stack

- **Framework**: FastAPI 0.109+
- **Database**: SQLite3 with aiosqlite driver
- **ORM**: SQLAlchemy 2.0 async
- **Migrations**: Alembic
- **Authentication**: JWT with python-jose, bcrypt password hashing
- **Testing**: pytest with pytest-asyncio, in-memory SQLite
- **Validation**: Pydantic 2.5+

---

## 📖 Plan Structure

Each plan includes:

1. **Summary**: High-level overview
2. **Architecture Mapping**: Domain → Infrastructure → API
3. **File Actions**: Files to create/modify
4. **Dependencies**: Required packages
5. **Data Persistence**: SQLAlchemy models, repositories, migrations
6. **API Endpoints**: Complete endpoint specifications
7. **Error Handling**: Domain exception mapping
8. **Testing Strategy**: Unit, integration, contract tests
9. **Open Questions**: Unresolved decisions
10. **Implementation Checklist**: Step-by-step tasks

---

## 🎯 Clean Architecture Principles

All plans follow:

- **Domain Layer**: Pure Python entities, zero framework dependencies
- **Infrastructure Layer**: SQLAlchemy models, repository implementations, external services
- **API Layer**: FastAPI routers, Pydantic schemas, dependency injection
- **Dependency Rule**: Domain ← Infrastructure ← API (never reverse)

---

## 🧪 Testing Strategy

- **Unit Tests**: Domain logic (pure Python)
- **Repository Tests**: SQLAlchemy operations with in-memory SQLite
- **Integration Tests**: Full HTTP request/response cycle
- **Contract Tests**: API schema validation
- **Target Coverage**: 80%+ across all layers

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**Last Updated**: 2025-11-13
**Status**: All plans ready for implementation
