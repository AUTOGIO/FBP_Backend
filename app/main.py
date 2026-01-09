"""FastAPI application entry point."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.execution_runtime import execution_runtime
from app.core.jobs import job_store
from app.core.logging_config import setup_logger
from app.modules.cad_redesim_consulta import (
    router as cad_redesim_consulta_router,
)
from app.modules.nfa_consult import router as nfa_consult_router
from app.routers import (
    echo,
    executor,
    global_router,
    health,
    n8n_browser,
    n8n_nfa,
    n8n_redesim,
    n8n_utils,
    nfa,
    nfa_real,
    redesim,
    telemetry,
)

# Setup logger
logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup
    project_info = f"{settings.PROJECT_NAME} v{settings.PROJECT_VERSION}"
    logger.info(f"Starting {project_info}")
    logger.info(f"Machine: {settings.MACHINE_INFO}")

    # Start job cleanup task
    cleanup_task = asyncio.create_task(job_store.cleanup_expired_jobs())
    logger.info("Job cleanup task started")

    yield

    # Shutdown
    await execution_runtime.shutdown()
    cleanup_task.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup_task
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Global FastAPI Backend for automation projects",
    lifespan=lifespan,
)

# CORS middleware for Cloudflare Zero Trust tunnel access
allowed_origins = [
    origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(echo.router)
app.include_router(executor.router)
app.include_router(global_router.router)  # Global unified endpoints
app.include_router(nfa.router)  # Phase 1 mock endpoints
app.include_router(nfa_real.router)  # Phase 2 real NFA endpoints
app.include_router(nfa_consult_router)  # NFA consultation automation
app.include_router(cad_redesim_consulta_router)  # REDESIM consulta (fixed filters)
app.include_router(redesim.router)  # Phase 2 REDESIM endpoints

# n8n-compatible endpoints
app.include_router(n8n_redesim.router)
app.include_router(n8n_nfa.router)
app.include_router(n8n_utils.router)
app.include_router(n8n_browser.router)

# Telemetry monitoring
app.include_router(telemetry.router)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "running",
    }


@app.get("/socket-health")
async def socket_health() -> dict:
    """UNIX socket health check endpoint.

    Returns:
        Socket status and path information
    """
    import os

    socket_path = settings.socket_path
    socket_exists = socket_path.exists() if socket_path else False

    return {
        "status": "ok",
        "via": "unix",
        "socket_path": str(socket_path),
        "socket_exists": socket_exists,
        "socket_permissions": (
            oct(os.stat(socket_path).st_mode)[-3:] if socket_exists else None
        ),
    }


@app.get("/metrics")
async def root_metrics() -> dict:
    """Root-level metrics endpoint (alias for /api/v1/telemetry/metrics).

    Returns:
        System metrics from telemetry service
    """
    from app.services.telemetry import get_system_metrics

    return get_system_metrics()


@app.get("/system/status")
async def system_status() -> dict:
    """Root-level system status endpoint.

    Returns:
        System health status
    """
    from app.services.telemetry import check_system_health

    return check_system_health()
