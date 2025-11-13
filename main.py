"""Main FastAPI application entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config.settings import settings
from config.database import init_db, close_db
from shared.exceptions import (
    DomainException,
    EntityNotFound,
    ValidationError,
    Unauthorized,
    Forbidden,
    InsufficientSeats,
    BookingAlreadyExists,
)

# Import routers (uncomment as implemented)
from apps.users.api.urls import router as users_router
from apps.trips.api.urls import router as trips_router
from apps.matching.api.urls import matching_router
from apps.maps.api.urls import maps_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events."""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    if settings.DEBUG:
        print("⚠️  Running in DEBUG mode")
        await init_db()  # Auto-create tables in development
    print("✅ Database initialized")

    yield

    # Shutdown
    print("👋 Shutting down application...")
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    description="API para sistema de carpooling con Clean Architecture"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(EntityNotFound)
async def entity_not_found_handler(request: Request, exc: EntityNotFound):
    """Handle entity not found exceptions."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle domain validation errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(Unauthorized)
async def unauthorized_handler(request: Request, exc: Unauthorized):
    """Handle unauthorized errors."""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(Forbidden)
async def forbidden_handler(request: Request, exc: Forbidden):
    """Handle forbidden errors."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(InsufficientSeats)
async def insufficient_seats_handler(request: Request, exc: InsufficientSeats):
    """Handle insufficient seats errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(BookingAlreadyExists)
async def booking_already_exists_handler(request: Request, exc: BookingAlreadyExists):
    """Handle booking already exists errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.message, "code": exc.code}
    )


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    """Handle all other domain exceptions."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": exc.code}
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns application status and basic information.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "sqlite",
        "debug": settings.DEBUG
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Include routers (uncomment as modules are implemented)
# Auth endpoints (register, login)
app.include_router(users_router, prefix="/api/v1/auth")
# User management endpoints (profile, etc.)
app.include_router(users_router, prefix="/api/v1/users")
# Trips endpoints
app.include_router(trips_router, prefix="/api/v1/trips")
# Maps endpoints
app.include_router(maps_router, prefix="/api/v1/maps")
# Matching endpoints
app.include_router(matching_router, prefix="/api/v1/matching")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.DEBUG,
        log_level="info"
    )
