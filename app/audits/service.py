import datetime
from datetime import timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.audits.models import Auditoria, Vulnerabilidad, MapeoEstandar, TareaRemediacion, EstadoAuditoria
from app.audits.orchestrator import AuditOrchestrator
from app.exceptions import NotFoundException


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.orchestrator = AuditOrchestrator(db)

    async def create_audit(self, proyecto_id: int, user_id: int,
                           frameworks: Optional[list] = None,
                           git_url: Optional[str] = None,
                           nombre: Optional[str] = None) -> Auditoria:
        audit = Auditoria(
            proyecto_id=proyecto_id,
            user_id=user_id,
            nombre=nombre or f"Auditoría #{proyecto_id}",
            estado=EstadoAuditoria.PENDIENTE.value,
            frameworks=frameworks or ["owasp", "nist_csf", "iso_27001", "cis", "mitre_attck"],
            git_url=git_url,
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit

    async def start_audit(self, audit_id: int) -> Auditoria:
        audit = await self.get_audit(audit_id)
        audit.estado = EstadoAuditoria.EJECUTANDO.value
        await self.db.commit()
        return audit

    async def run_audit_async(self, audit_id: int) -> dict:
        audit = await self.get_audit(audit_id)
        return await self.orchestrator.run_audit(audit)

    async def get_audit(self, audit_id: int) -> Auditoria:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Auditoria)
            .options(selectinload(Auditoria.proyecto))
            .where(Auditoria.id == audit_id)
        )
        audit = result.scalar_one_or_none()
        if not audit:
            raise NotFoundException("Auditoría no encontrada")
        return audit

    async def get_audit_progress(self, audit_id: int) -> dict:
        import json
        audit = await self.get_audit(audit_id)
        vulns = await self.get_audit_vulnerabilities(audit_id)
        raw = audit.resultado_resumen
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except: raw = {}
        elif raw is None:
            raw = {}
        progress = raw.get("progress", {}) if isinstance(raw, dict) else {}
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for v in vulns:
            if v.cvss_score is not None:
                if v.cvss_score >= 9.0: severity_counts["critical"] += 1
                elif v.cvss_score >= 7.0: severity_counts["high"] += 1
                elif v.cvss_score >= 4.0: severity_counts["medium"] += 1
                else: severity_counts["low"] += 1
        frameworks = audit.frameworks or []
        if isinstance(frameworks, str):
            try: frameworks = json.loads(frameworks)
            except: frameworks = []
        if not isinstance(frameworks, list):
            frameworks = []
        return {
            "audit_id": audit.id,
            "estado": audit.estado,
            "percentage": progress.get("percentage", 0 if audit.estado == "pendiente" else 100),
            "steps": progress.get("steps", []),
            "message": progress.get("message", ""),
            "vulnerabilities_found": len(vulns),
            "severity": severity_counts,
            "frameworks": frameworks,
        }

    async def get_project_audits(self, proyecto_id: int) -> list[Auditoria]:
        result = await self.db.execute(
            select(Auditoria).where(Auditoria.proyecto_id == proyecto_id)
            .order_by(Auditoria.created_at.desc())
        )
        return result.scalars().all()

    async def get_user_audits(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Auditoria]:
        from sqlalchemy.orm import selectinload
        from sqlalchemy import distinct
        result = await self.db.execute(
            select(Auditoria)
            .options(selectinload(Auditoria.proyecto))
            .where(Auditoria.user_id == user_id)
            .distinct()
            .offset(skip).limit(limit).order_by(Auditoria.created_at.desc())
        )
        return result.scalars().all()

    async def get_all_audits(self, skip: int = 0, limit: int = 100) -> list[Auditoria]:
        from sqlalchemy.orm import selectinload
        from sqlalchemy import distinct
        result = await self.db.execute(
            select(Auditoria)
            .options(selectinload(Auditoria.proyecto))
            .distinct()
            .offset(skip).limit(limit).order_by(Auditoria.created_at.desc())
        )
        return result.scalars().all()

    async def is_admin_role(self, user_id: int) -> bool:
        from app.auth.models import Usuario
        result = await self.db.execute(select(Usuario.rol_id).where(Usuario.id == user_id))
        rol_id = result.scalar_one_or_none()
        return rol_id == 1

    async def get_proyecto_nombre(self, proyecto_id: int) -> str:
        from app.projects.models import Proyecto
        result = await self.db.execute(select(Proyecto.nombre).where(Proyecto.id == proyecto_id))
        name = result.scalar_one_or_none()
        return name or "—"

    async def get_audit_vulnerabilities(self, audit_id: int) -> list[Vulnerabilidad]:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Vulnerabilidad)
            .options(selectinload(Vulnerabilidad.archivo), selectinload(Vulnerabilidad.mapeos), selectinload(Vulnerabilidad.tareas))
            .where(Vulnerabilidad.auditoria_id == audit_id)
        )
        return result.scalars().all()

    async def get_vulnerability(self, vuln_id: int) -> Vulnerabilidad:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Vulnerabilidad)
            .options(selectinload(Vulnerabilidad.archivo), selectinload(Vulnerabilidad.mapeos), selectinload(Vulnerabilidad.tareas))
            .where(Vulnerabilidad.id == vuln_id)
        )
        vuln = result.scalar_one_or_none()
        if not vuln:
            raise NotFoundException("Vulnerabilidad no encontrada")
        return vuln

    async def update_vulnerability_status(self, vuln_id: int, status: str) -> Vulnerabilidad:
        vuln = await self.get_vulnerability(vuln_id)
        vuln.resuelta = status
        await self.db.commit()
        await self.db.refresh(vuln)
        return vuln

    async def get_audit_summary(self, user_id: Optional[int] = None) -> dict:
        query = select(Auditoria)
        if user_id:
            query = query.where(Auditoria.user_id == user_id)

        result = await self.db.execute(query)
        audits = result.scalars().all()

        total = len(audits)
        completed = sum(1 for a in audits if a.estado == "completada")
        failed = sum(1 for a in audits if a.estado == "fallida")
        pending = sum(1 for a in audits if a.estado == "pendiente")
        running = sum(1 for a in audits if a.estado == "ejecutando")

        vuln_query = select(Vulnerabilidad)
        if user_id:
            vuln_query = vuln_query.join(Auditoria).where(Auditoria.user_id == user_id)
        vuln_result = await self.db.execute(vuln_query)
        vulns = vuln_result.scalars().all()

        return {
            "total_audits": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "running": running,
            "total_vulnerabilities": len(vulns),
            "critical": sum(1 for v in vulns if v.cvss_score and v.cvss_score >= 9.0),
            "high": sum(1 for v in vulns if v.cvss_score and 7.0 <= v.cvss_score < 9.0),
            "medium": sum(1 for v in vulns if v.cvss_score and 4.0 <= v.cvss_score < 7.0),
            "low": sum(1 for v in vulns if v.cvss_score and v.cvss_score < 4.0),
        }

    async def reset_stuck_audits(self) -> int:
        result = await self.db.execute(
            select(Auditoria).where(Auditoria.estado == "ejecutando")
            .where(Auditoria.created_at < datetime.utcnow() - timedelta(hours=1))
        )
        stuck = result.scalars().all()
        count = 0
        for a in stuck:
            a.estado = "fallida"
            a.completed_at = datetime.utcnow()
            count += 1
        await self.db.commit()
        return count
