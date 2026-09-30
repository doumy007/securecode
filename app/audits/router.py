import asyncio
import datetime
import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db, async_session_factory
from app.config import settings
from app.audits.service import AuditService
from app.audits.schemas import (
    AuditoriaCreate, AuditoriaResponse, VulnerabilidadResponse,
    MapeoEstandarResponse, TareaRemediacionResponse,
)
from app.dependencies import get_current_active_user, require_role, ensure_project_access, ensure_audit_access
from app.auth.models import Usuario
from app.ai.analyzer import AIAnalyzer
from app.shared.cache import cache

# La lista de auditorías se cachea brevemente: cambia con cada avance del
# worker, pero 8 s de TTL bastan para que la página cargue sin pegarle a la
# BD remota (lenta) en cada visita. Se invalida al crear/eliminar/resetear.
AUDITS_LIST_TTL = 8

logger = logging.getLogger("securecode.audit")

router = APIRouter()


@router.post("/", response_model=AuditoriaResponse, status_code=status.HTTP_201_CREATED)
async def create_audit(
    data: AuditoriaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    await ensure_project_access(db, data.proyecto_id, current_user)
    audit = await service.create_audit(
        proyecto_id=data.proyecto_id,
        user_id=current_user.id,
        nombre=data.nombre,
        frameworks=data.frameworks,
        git_url=data.git_url,
        git_username=data.git_username,
        git_token=data.git_token,
    )
    cache.clear_prefix("audits:list:")
    cache.clear_prefix("dash:")

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
    is_admin = current_user.rol.nombre == "admin"
    cache_key = f"audits:list:{'admin' if is_admin else current_user.id}:{skip}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if is_admin:
        audits = await service.get_all_audits(skip, limit)
    else:
        audits = await service.get_user_audits(current_user.id, skip, limit)

    vuln_counts, proj_names = await service.get_audits_list_meta(audits)
    result = []
    for a in audits:
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
            vulnerabilities_count=vuln_counts.get(a.id, 0),
            proyecto_nombre=proj_names.get(a.proyecto_id),
        ))
    cache.set(cache_key, result, ttl_seconds=AUDITS_LIST_TTL)
    return result


@router.get("/summary", response_model=dict)
async def get_audit_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    is_admin = current_user.rol.nombre == "admin"
    if is_admin:
        return await service.get_audit_summary()
    return await service.get_audit_summary(current_user.id)


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


@router.get("/{audit_id}", response_model=AuditoriaResponse)
async def get_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    await ensure_audit_access(db, audit_id, current_user)
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
    await ensure_audit_access(db, audit_id, current_user)
    return await service.get_audit_progress(audit_id)


@router.post("/reset-stuck")
async def reset_stuck_audits(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuditService(db)
    count = await service.reset_stuck_audits()
    cache.clear_prefix("audits:list:")
    cache.clear_prefix("dash:")
    return {"message": f"{count} auditorías atascadas reseteadas a fallida", "count": count}


@router.delete("/{audit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    await ensure_audit_access(db, audit_id, current_user)
    audit = await service.get_audit(audit_id)
    proyecto_id = audit.proyecto_id
    # Borrado masivo por SQL en orden de dependencias (FK): el borrado ORM
    # emitía un DELETE por fila a través de la BD remota (lento en auditorías
    # con miles de vulnerabilidades) y podía superar el timeout del frontend.
    await db.execute(
        text("DELETE FROM sc_historial_ejecuciones WHERE auditoria_id = :aid"), {"aid": audit_id}
    )
    await db.execute(
        text(
            "DELETE FROM sc_mapeo_estandares "
            "WHERE vulnerabilidad_id IN ("
            "SELECT id FROM sc_vulnerabilidades WHERE auditoria_id = :aid)"
        ),
        {"aid": audit_id},
    )
    await db.execute(
        text("DELETE FROM sc_tareas_remediacion WHERE auditoria_id = :aid"), {"aid": audit_id}
    )
    await db.execute(
        text("DELETE FROM sc_resultados_worker WHERE auditoria_id = :aid"), {"aid": audit_id}
    )
    await db.execute(
        text("DELETE FROM sc_vulnerabilidades WHERE auditoria_id = :aid"), {"aid": audit_id}
    )
    # Libera el snapshot de código de la auditoría borrada: solo filas que
    # ninguna otra auditoría siga referenciando por archivo.
    await db.execute(
        text(
            "DELETE FROM sc_archivos_proyecto "
            "WHERE auditoria_id = :aid "
            "AND id NOT IN (SELECT archivo_id FROM sc_vulnerabilidades WHERE archivo_id IS NOT NULL)"
        ),
        {"aid": audit_id},
    )
    await db.execute(
        text("DELETE FROM sc_auditorias WHERE id = :aid"), {"aid": audit_id}
    )
    await db.commit()
    cache.clear_prefix("audits:list:")
    cache.clear_prefix("dash:")
    if proyecto_id:
        cache.clear_prefix(f"projects:list:")


@router.get("/{audit_id}/vulnerabilities", response_model=List[VulnerabilidadResponse])
async def get_audit_vulnerabilities(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    await ensure_audit_access(db, audit_id, current_user)
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
    await ensure_audit_access(db, audit_id, current_user)
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
    v = await service.get_vulnerability(vuln_id)
    await ensure_audit_access(db, v.auditoria_id, current_user)
    await service.update_vulnerability_status(vuln_id, status)
    return {"message": "Estado actualizado"}


# ---------------------------------------------------------------------------
# Informes por framework: generación en SEGUNDO PLANO con polling.
# ---------------------------------------------------------------------------
# Antes la generación IA corría inline dentro de la petición (24-28 s frente
# al timeout de 30 s del frontend) y el worker pisaba resultado_resumen con
# {"reports": {}} al completar la auditoría, PERDIENDO informes ya generados
# (por eso a veces "aparecía y luego error", o había que apretar dos veces).
# Ahora:
#  - si el informe ya está cacheado en resultado_resumen -> respuesta directa;
#  - si no, se agenda una tarea asíncrona de generación y la petición devuelve
#    {"status":"pending"} para que el frontend haga polling sin timeouts;
#  - la tarea guarda con read-modify-write (merge, nunca pisa otras claves) y
#    hay deduplicación por (audit_id, framework) para no gastar OpenAI 2 veces.
_report_tasks: dict = {}          # (audit_id, framework) -> asyncio.Task
_report_tasks_lock = asyncio.Lock()
_report_failures: dict = {}       # (audit_id, framework) -> timestamp

REPORT_GEN_TIMEOUT_SECONDS = 300.0


async def _build_report_findings(db: AsyncSession, audit) -> list:
    """Prepara los hallazgos (misma forma que la vista del informe) para
    alimentar el prompt del informe por framework."""
    vulns = await AuditService(db).get_audit_vulnerabilities(audit.id)
    findings = []
    for v in vulns:
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
    return findings


def _report_is_valid(cached) -> bool:
    """Un informe cacheado no es válido si contiene el mosaico de error que
    devuelve el generador cuando OpenAI falla."""
    return bool(
        cached
        and isinstance(cached, dict)
        and not (cached.get("report_metadata") or {}).get("error")
    )


async def _save_report_merge(db: AsyncSession, audit, framework: str, report: dict):
    """Guarda el informe haciendo MERGE sobre resultado_resumen: preserva
    progress, totales y otros informes ya existentes (nunca pisa)."""
    raw = audit.resultado_resumen
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    reports = raw.get("reports")
    if not isinstance(reports, dict):
        reports = {}
    reports[framework] = report
    raw["reports"] = reports
    await db.execute(
        text("UPDATE sc_auditorias SET resultado_resumen = :val, updated_at = :ts WHERE id = :id"),
        {"val": json.dumps(raw), "id": audit.id, "ts": datetime.datetime.utcnow()},
    )
    await db.commit()


async def _generate_report_background(audit_id: int, framework: str):
    try:
        async with async_session_factory() as db:
            service = AuditService(db)
            audit = await service.get_audit(audit_id)
            findings = await _build_report_findings(db, audit)
            project = audit.proyecto
            ai = AIAnalyzer()
            try:
                report = await asyncio.wait_for(
                    ai.generate_framework_report(
                        framework,
                        {"id": audit.id, "fecha": audit.created_at.isoformat() if audit.created_at else ""},
                        findings,
                        {"id": project.id, "nombre": project.nombre if project else "—"},
                    ),
                    timeout=REPORT_GEN_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error(f"Generación de informe {framework} (audit {audit_id}) excedió {REPORT_GEN_TIMEOUT_SECONDS}s")
                report = None

            # El generador devuelve un dict con report_metadata.error cuando
            # OpenAI falla: no lo cacheamos para poder reintentar después.
            if report is None or (report.get("report_metadata") or {}).get("error"):
                _report_failures[(audit_id, framework)] = time.time()
                logger.error(
                    f"No se pudo generar informe {framework} (audit {audit_id}): "
                    f"{report and report.get('report_metadata', {}).get('error') or 'sin respuesta'}"
                )
                return

            await _save_report_merge(db, audit, framework, report)
            _report_failures.pop((audit_id, framework), None)
            logger.info(f"Informe {framework} (audit {audit_id}) generado y cacheado")
    except Exception as e:
        logger.exception(f"Error generando informe {framework} (audit {audit_id})")
        _report_failures[(audit_id, framework)] = time.time()
    finally:
        _report_tasks.pop((audit_id, framework), None)


@router.get("/{audit_id}/report/{framework}")
async def get_framework_report(
    audit_id: int,
    framework: str,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = AuditService(db)
    await ensure_audit_access(db, audit_id, current_user)
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
    cached = reports_cache.get(framework) if isinstance(reports_cache, dict) else None
    if _report_is_valid(cached):
        return cached

    # Generación en segundo plano (una sola por auditoría+framework).
    key = (audit_id, framework)
    async with _report_tasks_lock:
        if key in _report_tasks:
            return {"status": "pending", "retry_after_ms": 2000}
        fail_ts = _report_failures.get(key)
        if fail_ts and time.time() - fail_ts < 60:
            # OpenAI caído: recupera por sí solo y no martillear con 2 s.
            return {"status": "pending", "retry_after_ms": 15000}
        task = asyncio.create_task(_generate_report_background(audit_id, framework))
        _report_tasks[key] = task
    return {"status": "pending", "retry_after_ms": 2000}
