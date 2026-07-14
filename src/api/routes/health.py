"""Health / root."""

from fastapi import APIRouter

from src.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/")
def read_root():
    return {
        "status": "online",
        "game": "League of Legends Manager",
        "engine_version": "1.0.0",
        "environment": settings.environment,
    }
