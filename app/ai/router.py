from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.dependencies import get_current_active_user
from app.auth.models import Usuario
from app.ai.chat import AuditChat
from app.audits.service import AuditService

router = APIRouter()
chat = AuditChat()


class ChatRequest(BaseModel):
    audit_id: int
    question: str


class ChatResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=ChatResponse)
async def audit_chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    audit = await service.get_audit(data.audit_id)

    audit_context = {
        "audit_id": audit.id,
        "proyecto_id": audit.proyecto_id,
        "estado": audit.estado,
        "proyecto_nombre": audit.proyecto.nombre if audit.proyecto else "Unknown",
        "vulnerabilidades": [
            {
                "nombre": v.nombre,
                "tipo": v.tipo,
                "severidad": v.severidad,
                "descripcion": v.descripcion,
                "cvss_score": v.cvss_score,
                "recomendacion": v.recomendacion,
                "codigo_vulnerable": v.codigo_vulnerable,
                "codigo_corregido": v.codigo_corregido,
            }
            for v in audit.vulnerabilidades
        ],
    }

    answer = await chat.ask(data.audit_id, data.question, audit_context)
    return ChatResponse(answer=answer)


@router.post("/chat/clear")
async def clear_chat_history(
    audit_id: int,
    current_user: Usuario = Depends(get_current_active_user),
):
    chat.clear_history(audit_id)
    return {"message": "Historial de chat limpiado"}
