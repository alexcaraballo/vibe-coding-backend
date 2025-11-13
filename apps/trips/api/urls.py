"""URL router aggregator for trips module."""
from fastapi import APIRouter
from apps.trips.api.versioning.v1.views import router as v1_router
from apps.trips.api.versioning.v1.chat_views import router as chat_router

router = APIRouter()
router.include_router(v1_router, tags=["Trips"])
router.include_router(chat_router, tags=["Chat"])
