"""Router aggregator for User API.

This module combines all user-related routers and exposes them
as a single router for registration in main.py.
"""
from fastapi import APIRouter

from apps.users.api.versioning.v1.views import router as v1_router

# Create main router for users module
router = APIRouter()

# Include v1 router
router.include_router(v1_router, tags=["Users & Auth"])
