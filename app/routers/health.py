"""Health check router."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status with machine and project info

    """
    return {
        "status": "ok",
        "machine": settings.MACHINE_INFO,
        "project": settings.PROJECT_NAME,
    }
