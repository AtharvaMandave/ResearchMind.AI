"""
ResearchMind AI – FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import engine
from app.models import Base
from app.api import projects as projects_router
from app.api import reports as reports_router
from app.api import uploads as uploads_router
from app.api import ws as ws_router

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:  Create all DB tables if they don't exist (for quick dev iteration).
              In production, use Alembic migrations instead.
    Shutdown: Dispose the async connection pool.
    """
    logger.info("🚀 ResearchMind AI starting up...")

    # Note: In production comment out the create_all and rely on Alembic.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified/created.")

    yield

    logger.info("🛑 Shutting down...")
    await engine.dispose()
    logger.info("✅ DB connection pool closed.")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "ResearchMind AI – Autonomous Research Agent API.\n\n"
        "Accepts a research topic, autonomously searches the web and literature, "
        "critiques sources, detects contradictions and research gaps, and "
        "generates a citation-backed report."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(projects_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
app.include_router(uploads_router.router, prefix="/api/v1")
app.include_router(ws_router.router, prefix="/api/v1")


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check endpoint")
async def health_check():
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }
    )


# ── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", tags=["System"], include_in_schema=False)
async def root():
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/health",
    }
