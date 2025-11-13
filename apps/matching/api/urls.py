"""Matching API URL configuration."""
from fastapi import APIRouter
from apps.matching.api.versioning.v1 import views as v1_views

# Aggregate all matching routes
matching_router = APIRouter()

# Include v1 routes
matching_router.include_router(v1_views.router, prefix="/v1", tags=["Matching"])
