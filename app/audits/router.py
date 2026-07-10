from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.audits.service import AuditService
from app.audits.schemas import (
    AuditoriaCreate, AuditoriaResponse, VulnerabilidadResponse,
    MapeoEstandarResponse, TareaRemediacionResponse,
)
from app.dependencies import get_current_active_user
from app.auth.models import Usuario

router = APIRouter()


@router.post("/", response_model=AuditoriaResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    data: AuditoriaCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    audit = await service.create_audit(
        proyecto_id=data.proyecto_id,
        user_id=current_user.id,
        nombre=data.nombre,
        frameworks=data.frameworks,
        git_url=data.git_url,
    )

    background_tasks.add_task(service.run_audit_async, audit.id)

    nombre_proyecto = await service.get_proyecto_nombre(audit.proyecto_id)
    return AuditoriaResponse(
        id=audit.id,
        proyecto_id=audit.proyecto_id,
        user_id=audit.user_id,
        nombre=audit.nombre,
        estado=audit.estado,
        tipo=audit.tipo,
        version=audit.version,
        resultado_resumen=audit.resultado_resumen,
        frameworks=audit.frameworks,
        git_url=audit.git_url,
        created_at=audit.created_at,
        completed_at=audit.completed_at,
        proyecto_nombre=nombre_proyecto,
    )


@router.get("/", response_model=List[AuditoriaResponse])
async def list_audits(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    is_admin = await service.is_admin_role(current_user.id)
    if is_admin:
        audits = await service.get_all_audits(skip, limit)
    else:
        audits = await service.get_user_audits(current_user.id, skip, limit)

    result = []
    for a in audits:
        vulns = await service.get_audit_vulnerabilities(a.id)
        nombre_proyecto = await service.get_proyecto_nombre(a.proyecto_id)
        result.append(AuditoriaResponse(
            id=a.id,
            proyecto_id=a.proyecto_id,
            user_id=a.user_id,
            nombre=a.nombre,
            estado=a.estado,
            tipo=a.tipo,
            version=a.version,
            resultado_resumen=a.resultado_resumen,
            frameworks=a.frameworks,
            git_url=a.git_url,
            created_at=a.created_at,
            completed_at=a.completed_at,
            vulnerabilities_count=len(vulns),
            proyecto_nombre=nombre_proyecto,
        ))
    return result


@router.get("/{audit_id}", response_model=AuditoriaResponse)
async def get_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    audit = await service.get_audit(audit_id)
    vulns = await service.get_audit_vulnerabilities(audit_id)
    nombre_proyecto = await service.get_proyecto_nombre(audit.proyecto_id)
    return AuditoriaResponse(
        id=audit.id,
        proyecto_id=audit.proyecto_id,
        user_id=audit.user_id,
        nombre=audit.nombre,
        estado=audit.estado,
        tipo=audit.tipo,
        version=audit.version,
        resultado_resumen=audit.resultado_resumen,
        frameworks=audit.frameworks,
        git_url=audit.git_url,
        created_at=audit.created_at,
        completed_at=audit.completed_at,
        vulnerabilities_count=len(vulns),
        proyecto_nombre=nombre_proyecto,
    )


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    audit = await service.get_audit(audit_id)
    await db.delete(audit)
    await db.commit()


@router.get("/{audit_id}/vulnerabilities", response_model=List[VulnerabilidadResponse])
async def get_audit_vulnerabilities(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    vulns = await service.get_audit_vulnerabilities(audit_id)
    result = []
    for v in vulns:
        result.append(VulnerabilidadResponse(
            id=v.id,
            auditoria_id=v.auditoria_id,
            archivo_id=v.archivo_id,
            tipo=v.tipo,
            nombre=v.nombre,
            descripcion=v.descripcion,
            severidad=v.severidad,
            cvss_score=v.cvss_score,
            impacto=v.impacto,
            probabilidad=v.probabilidad,
            prioridad=v.prioridad,
            linea_inicio=v.linea_inicio,
            linea_fin=v.linea_fin,
            codigo_vulnerable=v.codigo_vulnerable,
            codigo_corregido=v.codigo_corregido,
            recomendacion=v.recomendacion,
            fuente=v.fuente,
            resuelta=v.resuelta,
            created_at=v.created_at,
            archivo_ruta=v.archivo.ruta if v.archivo else None,
            mapeos=[{"id": m.id, "estandar": m.estandar, "categoria": m.categoria, "referencia": m.referencia} for m in v.mapeos] if v.mapeos else [],
            tareas=[{"id": t.id, "paso": t.paso, "descripcion": t.descripcion, "prioridad": t.prioridad, "estado": t.estado} for t in v.tareas] if v.tareas else [],
        ))
    return result


@router.get("/{audit_id}/vulnerabilities/{vuln_id}", response_model=VulnerabilidadResponse)
async def get_vulnerability(
    audit_id: int,
    vuln_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    v = await service.get_vulnerability(vuln_id)
    return VulnerabilidadResponse(
        id=v.id,
        auditoria_id=v.auditoria_id,
        archivo_id=v.archivo_id,
        tipo=v.tipo,
        nombre=v.nombre,
        descripcion=v.descripcion,
        severidad=v.severidad,
        cvss_score=v.cvss_score,
        impacto=v.impacto,
        probabilidad=v.probabilidad,
        prioridad=v.prioridad,
        linea_inicio=v.linea_inicio,
        linea_fin=v.linea_fin,
        codigo_vulnerable=v.codigo_vulnerable,
        codigo_corregido=v.codigo_corregido,
        recomendacion=v.recomendacion,
        fuente=v.fuente,
        resuelta=v.resuelta,
        created_at=v.created_at,
        archivo_ruta=v.archivo.ruta if v.archivo else None,
    )


@router.put("/vulnerabilities/{vuln_id}/status")
async def update_vulnerability_status(
    vuln_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    await service.update_vulnerability_status(vuln_id, status)
    return {"message": "Estado actualizado"}


@router.get("/frameworks")
async def list_frameworks():
    return [
        {"id": "owasp", "label": "OWASP Top 10", "desc": "Seguridad en aplicaciones web"},
        {"id": "nist_csf", "label": "NIST CSF", "desc": "Framework de Ciberseguridad"},
        {"id": "nist_800_82", "label": "NIST SP 800-82", "desc": "Seguridad en ICS/SCADA"},
        {"id": "iso_27001", "label": "ISO 27001", "desc": "Sistema de Gestión de Seguridad"},
        {"id": "cis", "label": "CIS Controls v8", "desc": "Controles de seguridad críticos"},
        {"id": "mitre_attck", "label": "MITRE ATT&CK", "desc": "Tácticas y técnicas adversariales"},
    ]


@router.get("/summary", response_model=dict)
async def get_audit_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    is_admin = await service.is_admin_role(current_user.id)
    if is_admin:
        return await service.get_audit_summary()
    return await service.get_audit_summary(current_user.id)
