import asyncio
import logging
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
import app.models  # noqa: F401  # registra todos los modelos SQLAlchemy (mappers)
from app.audits.service import AuditService
from app.config import settings

logger = logging.getLogger("securecode.worker")

# Minutos sin progreso antes de marcar una auditoría 'ejecutando' como fallida.
# Configurable por entorno (APP_AUDIT_TIMEOUT_MINUTES); por defecto 120 para
# no matar auditorías grandes contra la BD remota lenta.
AUDIT_TIMEOUT_MINUTES = settings.APP_AUDIT_TIMEOUT_MINUTES
POLL_INTERVAL_SECONDS = 5
# Backoff máximo cuando la BD está caída/indisponible (evita log spam y ciclos
# de trabajo inútiles).
MAX_BACKOFF_SECONDS = 300


async def watchdog(db: AsyncSession, service: AuditService) -> None:
    try:
        n = await service.watchdog_fail_stuck(max_minutes=AUDIT_TIMEOUT_MINUTES)
        if n:
            logger.warning(f"Watchdog: {n} auditoría(s) atascada(s) marcada(s) como fallida")
    except Exception as e:
        logger.error(f"Watchdog error: {e}")


async def process_pending_audits():
    backoff = POLL_INTERVAL_SECONDS
    while True:
        clean_pass = True
        try:
            async with async_session_factory() as db:
                service = AuditService(db)
                await watchdog(db, service)

                audits = await service.get_pending_audits()
                for audit in audits:
                    # Claim atómico: si otro worker/instancia ya lo tomó, se salta.
                    claimed = await service.claim_audit(audit.id)
                    if not claimed:
                        logger.info(f"Auditoría {audit.id} ya reclamada por otro proceso, se omite")
                        continue
                    logger.info(f"Procesando auditoría {audit.id} (proyecto {audit.proyecto_id})")
                    try:
                        await service.run_audit_async(audit.id)
                        logger.info(f"Auditoría {audit.id} finalizada")
                    except Exception as e:
                        logger.exception(f"Error ejecutando auditoría {audit.id}: {e}")
                        clean_pass = False
        except Exception as e:
            logger.error(f"Error en worker loop: {e}")
            clean_pass = False

        # Backoff exponencial: si hubo cualquier error (BD caída, etc.) se
        # espera cada vez más (hasta MAX_BACKOFF_SECONDS); al pasar un ciclo
        # limpio se vuelve al intervalo base.
        if clean_pass:
            backoff = POLL_INTERVAL_SECONDS
        else:
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
        await asyncio.sleep(backoff)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Iniciando Worker de SecureCode AI")
    asyncio.run(process_pending_audits())