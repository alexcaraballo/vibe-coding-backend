"""Maps API URL configuration."""
from fastapi import APIRouter
from apps.maps.api.versioning.v1 import views as v1_views

# Aggregate all map routes
maps_router = APIRouter()

# Include v1 routes
maps_router.include_router(v1_views.router, prefix="/v1", tags=["Maps"])
