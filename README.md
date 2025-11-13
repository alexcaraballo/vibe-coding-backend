# Vibe Coding - Sistema de Carpooling Backend

Backend API para sistema de carpooling construido con FastAPI siguiendo Clean Architecture (Arquitectura Hexagonal).

## 🏗️ Arquitectura

El proyecto sigue **Clean Architecture** con 3 capas claramente separadas:

- **Domain** (`apps/*/domain/`): Entidades de negocio puras, sin dependencias externas
- **Infrastructure** (`apps/*/infrastructure/`): Implementaciones de repositorios, servicios externos
- **API** (`apps/*/api/`): Endpoints REST, DTOs de entrada/salida

### Módulos

- **users**: Gestión de usuarios y autenticación
- **trips**: Publicación, búsqueda y reserva de trayectos
- **matching**: Motor de matching entre conductores y pasajeros
- **maps**: Integración con mapas y geocodificación

## 🚀 Tecnologías

- **FastAPI**: Framework web async
- **SQLAlchemy 2.0**: ORM con soporte async
- **SQLite3**: Base de datos (aiosqlite driver)
- **Alembic**: Migraciones de base de datos
- **Pydantic**: Validación de datos y settings
- **Poetry**: Gestión de dependencias

## 📋 Requisitos

- Python 3.11+
- Poetry

## 🛠️ Setup

### 1. Instalar dependencias

```bash
poetry install
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu configuración
```

### 3. Inicializar base de datos

```bash
# Opción 1: Auto-create tables (solo desarrollo)
# Se ejecuta automáticamente al arrancar con DEBUG=true

# Opción 2: Usar Alembic migrations (recomendado para producción)
poetry run alembic upgrade head
```

### 4. Ejecutar servidor

```bash
# Modo desarrollo (con auto-reload)
poetry run python main.py

# O usando uvicorn directamente
poetry run uvicorn main:app --reload
```

El servidor estará disponible en:
- API: http://localhost:8000
- Documentación interactiva (Swagger): http://localhost:8000/docs
- Documentación alternativa (ReDoc): http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## 🧪 Testing

```bash
# Ejecutar todos los tests
poetry run pytest

# Con coverage
poetry run pytest --cov=apps --cov-report=html

# Solo un módulo
poetry run pytest tests/test_users/

# Modo verbose
poetry run pytest -v
```

Los tests usan SQLite in-memory para mayor velocidad.

## 📊 Migraciones de Base de Datos

```bash
# Crear una nueva migración (auto-detecta cambios en modelos)
poetry run alembic revision --autogenerate -m "descripcion del cambio"

# Aplicar migraciones
poetry run alembic upgrade head

# Revertir última migración
poetry run alembic downgrade -1

# Ver historial de migraciones
poetry run alembic history
```

## 📁 Estructura del Proyecto

```
vibe-coding-backend/
├── apps/                       # Módulos de la aplicación
│   ├── users/                  # Gestión de usuarios
│   ├── trips/                  # Gestión de trayectos
│   ├── matching/               # Motor de matching
│   └── maps/                   # Integración con mapas
├── config/                     # Configuración global
│   ├── settings.py            # Variables de entorno
│   └── database.py            # Configuración de SQLAlchemy
├── shared/                     # Código compartido
│   ├── exceptions.py          # Excepciones del dominio
│   ├── validators.py          # Validadores comunes
│   └── utils.py               # Utilidades
├── migrations/                 # Migraciones de Alembic
├── tests/                      # Tests
├── main.py                     # Entry point FastAPI
├── pyproject.toml             # Dependencias
└── alembic.ini                # Configuración de Alembic
```

## 🔧 Comandos Útiles

```bash
# Formatear código
poetry run black .

# Linting
poetry run ruff check .

# Type checking
poetry run mypy .

# Instalar nueva dependencia
poetry add package-name

# Instalar dependencia de desarrollo
poetry add --group dev package-name
```

## 📝 Convenciones

### Flujo de Desarrollo

1. **Domain First**: Definir entidades y lógica de negocio
2. **Infrastructure**: Implementar repositorios y servicios
3. **API**: Crear endpoints y DTOs
4. **Tests**: Escribir tests para cada capa

### Reglas de Dependencias

- ✅ Domain NO depende de nada (solo Python puro)
- ✅ Infrastructure depende de Domain
- ✅ API depende de Infrastructure y Domain
- ❌ NUNCA importar de capas superiores hacia inferiores

### Parámetros de Funciones

```python
# ✅ CORRECTO: Parámetros sin default ANTES de los con default
async def create_user(repo: UserRepository, email: str, name: str = "Guest"):
    pass

# ❌ ERROR: SyntaxError
async def create_user(email: str = "test@example.com", repo: UserRepository):
    pass
```

## 🚦 Estado del Proyecto

- [x] Estructura inicial
- [x] Configuración base (SQLite, FastAPI, Alembic)
- [x] Módulos skeleton (users, trips, matching, maps)
- [ ] Módulo Users (autenticación)
- [ ] Módulo Trips
- [ ] Módulo Matching
- [ ] Módulo Maps

## 📚 Recursos

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## 👥 Equipo

Vibe Coding Team - Hackathon 2025
