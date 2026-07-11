import asyncio
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Set
from app.database import get_db, async_session_factory
from app.audits.service import AuditService
from app.audits.schemas import (
    AuditoriaCreate, AuditoriaResponse, VulnerabilidadResponse,
    MapeoEstandarResponse, TareaRemediacionResponse,
)
from app.dependencies import get_current_active_user, require_role
from app.auth.models import Usuario
from app.ai.analyzer import AIAnalyzer

logger = logging.getLogger("securecode.audit")

router = APIRouter()

_background_tasks: Set[asyncio.Task] = set()


@router.post("/", response_model=AuditoriaResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    data: AuditoriaCreate,
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
        git_username=data.git_username,
        git_token=data.git_token,
    )

    async def run_background():
        async with async_session_factory() as bg_db:
            bg_service = AuditService(bg_db)
            try:
                logger.info("Background audit %s started", audit.id)
                await bg_service.run_audit_async(audit.id)
                logger.info("Background audit %s finished", audit.id)
            except Exception as e:
                logger.exception("Background audit %s failed: %s", audit.id, e)
            await bg_db.commit()

    task = asyncio.create_task(run_background())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

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


@router.get("/{audit_id}/progress")
async def get_audit_progress(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    return await service.get_audit_progress(audit_id)


@router.post("/reset-stuck")
async def reset_stuck_audits(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuditService(db)
    count = await service.reset_stuck_audits()
    return {"message": f"{count} auditorías atascadas reseteadas a fallida", "count": count}


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
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


@router.get("/{audit_id}/report/{framework}")
async def get_framework_report(
    audit_id: int,
    framework: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    audit = await service.get_audit(audit_id)

    fw_list = audit.frameworks or []
    if isinstance(fw_list, str):
        try: fw_list = json.loads(fw_list)
        except: fw_list = []
    if framework not in fw_list:
        raise HTTPException(status_code=400, detail=f"Framework '{framework}' no seleccionado en esta auditoría")

    raw = audit.resultado_resumen
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except: raw = {}
    elif raw is None:
        raw = {}
    reports_cache = raw.get("reports", {}) if isinstance(raw, dict) else {}
    cached = reports_cache.get(framework)
    if cached:
        return cached

    vulns_orm = await service.get_audit_vulnerabilities(audit_id)
    project = audit.proyecto
    findings = []
    for v in vulns_orm:
        findings.append({
            "tipo": v.tipo,
            "archivo": v.archivo.ruta if v.archivo else None,
            "linea_inicio": v.linea_inicio,
            "linea_fin": v.linea_fin,
            "descripcion": v.descripcion,
            "severidad": v.severidad,
            "cvss_score": v.cvss_score,
            "codigo_vulnerable": v.codigo_vulnerable,
            "codigo_corregido": v.codigo_corregido,
            "recomendacion": v.recomendacion,
            "mapeos": [{"estandar": m.estandar, "categoria": m.categoria, "referencia": m.referencia} for m in v.mapeos] if v.mapeos else [],
        })

    project_info = {
        "id": project.id,
        "nombre": project.nombre if project else "—",
    }
    audit_info = {
        "id": audit.id,
        "fecha": audit.created_at.isoformat() if audit.created_at else "",
    }

    ai = AIAnalyzer()
    report = await ai.generate_framework_report(framework, audit_info, findings, project_info)

    raw["reports"] = raw.get("reports", {})
    raw["reports"][framework] = report
    await db.execute(
        text("UPDATE sc_auditorias SET resultado_resumen = :val WHERE id = :id"),
        {"val": json.dumps(raw), "id": audit.id},
    )
    await db.commit()

    return report


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
