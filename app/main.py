import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path
from app.config import settings
from app.middleware import setup_middlewares
from app.auth.router import router as auth_router
from app.projects.router import router as projects_router
from app.audits.router import router as audits_router
from app.dashboard.router import router as dashboard_router
from app.ai.router import router as ai_router
from app.integrations.router import router as integrations_router

logging.basicConfig(
    level=getattr(logging, settings.APP_LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("securecode")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    from app.database import init_db, async_session_factory
    await init_db()
    logger.info("Base de datos inicializada")
    async with async_session_factory() as startup_db:
        from sqlalchemy import select
        from app.audits.models import Auditoria
        result = await startup_db.execute(
            select(Auditoria).where(Auditoria.estado == "ejecutando")
        )
        stuck = result.scalars().all()
        for a in stuck:
            a.estado = "fallida"
            logger.info("Auditoría %s marcada como fallida por reinicio del servidor", a.id)
        if stuck:
            await startup_db.commit()
            logger.info("%s auditorías atascadas reseteadas", len(stuck))
    yield
    logger.info("Apagando servidor")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma Inteligente para Auditoría Automatizada de Seguridad y Cumplimiento Normativo",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_middlewares(app)

app.include_router(auth_router, prefix="/auth", tags=["Autenticación"])
app.include_router(projects_router, prefix="/projects", tags=["Proyectos"])
app.include_router(audits_router, prefix="/audits", tags=["Auditorías"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(ai_router, prefix="/ai", tags=["Inteligencia Artificial"])
app.include_router(integrations_router, prefix="/integrations", tags=["Integraciones"])

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning("static/ no encontrado, montando portal estático")


@app.get("/", include_in_schema=False)
async def portal_root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }
