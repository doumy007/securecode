import json
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("securecode.audits")

try:
    import aio_pika
    RABBIT_AVAILABLE = True
except ImportError:
    RABBIT_AVAILABLE = False
    logger.warning("aio-pika no disponible, usando modo directo")


class AuditScheduler:
    async def publish_task(self, audit_id: int):
        if not RABBIT_AVAILABLE:
            logger.info(f"Ejecutando auditoría {audit_id} en modo directo (sin RabbitMQ)")
            return

        try:
            connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue(settings.RABBITMQ_QUEUE, durable=True)

                message = aio_pika.Message(
                    body=json.dumps({"audit_id": audit_id}).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                )
                await channel.default_exchange.publish(message, routing_key=queue.name)
                logger.info(f"Tarea publicada en RabbitMQ: audit_id={audit_id}")
        except Exception as e:
            logger.error(f"Error publicando en RabbitMQ: {e}")
            logger.info(f"Ejecutando auditoría {audit_id} en modo directo (fallback)")
