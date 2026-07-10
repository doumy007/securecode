import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
from app.audits.service import AuditService

logger = logging.getLogger("securecode.worker")


async def process_pending_audits():
    while True:
        try:
            async with async_session_factory() as db:
                service = AuditService(db)
                audits = await service.get_all_audits()
                for audit in audits:
                    if audit.estado == "pendiente":
                        logger.info(f"Procesando auditoría pendiente: {audit.id}")
                        await service.run_audit_async(audit.id)
        except Exception as e:
            logger.error(f"Error en worker loop: {e}")

        await asyncio.sleep(10)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Iniciando Worker de SecureCode AI")
    asyncio.run(process_pending_audits())
