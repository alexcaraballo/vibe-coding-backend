"""URL router aggregator for trips module."""
from fastapi import APIRouter
from apps.trips.api.versioning.v1.views import router as v1_router

router = APIRouter()
router.include_router(v1_router, tags=["Trips"])
