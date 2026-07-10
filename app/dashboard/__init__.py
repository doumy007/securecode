from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.audits.models import Auditoria, Vulnerabilidad
from app.projects.models import Proyecto
from app.auth.models import Usuario
from typing import Optional


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _is_admin_role(self, user_id: int) -> bool:
        from app.auth.models import Usuario as U
        result = await self.db.execute(
            select(U.rol_id).where(U.id == user_id)
        )
        rol_id = result.scalar_one_or_none()
        return rol_id == 1  # admin rol

    async def get_kpi(self, user_id: Optional[int] = None) -> dict:
        audit_query = select(Auditoria)
        vuln_query = select(Vulnerabilidad)

        if user_id:
            audit_query = audit_query.where(Auditoria.user_id == user_id)
            vuln_query = vuln_query.join(Auditoria).where(Auditoria.user_id == user_id)

        audits = (await self.db.execute(audit_query)).scalars().all()
        vulns = (await self.db.execute(vuln_query)).scalars().all()

        proyectos = (await self.db.execute(select(func.count()).select_from(Proyecto))).scalar()
        usuarios = (await self.db.execute(select(func.count()).select_from(Usuario))).scalar()

        return {
            "total_proyectos": proyectos or 0,
            "total_auditorias": len(audits),
            "total_vulnerabilidades": len(vulns),
            "total_usuarios": usuarios or 0,
            "completed_audits": sum(1 for a in audits if a.estado == "completada"),
            "failed_audits": sum(1 for a in audits if a.estado == "fallida"),
            "critical": sum(1 for v in vulns if v.cvss_score and v.cvss_score >= 9.0),
            "high": sum(1 for v in vulns if v.cvss_score and 7.0 <= v.cvss_score < 9.0),
            "medium": sum(1 for v in vulns if v.cvss_score and 4.0 <= v.cvss_score < 7.0),
            "low": sum(1 for v in vulns if v.cvss_score and v.cvss_score < 4.0),
            "resolved": sum(1 for v in vulns if v.resuelta == "completada"),
            "compliance_score": self._calculate_compliance_score(vulns),
        }

    async def get_vulnerability_by_severity(self, user_id: Optional[int] = None) -> dict:
        vuln_query = select(Vulnerabilidad)
        if user_id:
            vuln_query = vuln_query.join(Auditoria).where(Auditoria.user_id == user_id)
        vulns = (await self.db.execute(vuln_query)).scalars().all()

        return {
            "critical": sum(1 for v in vulns if v.cvss_score and v.cvss_score >= 9.0),
            "high": sum(1 for v in vulns if v.cvss_score and 7.0 <= v.cvss_score < 9.0),
            "medium": sum(1 for v in vulns if v.cvss_score and 4.0 <= v.cvss_score < 7.0),
            "low": sum(1 for v in vulns if v.cvss_score and v.cvss_score < 4.0),
            "labels": ["Crítica", "Alta", "Media", "Baja"],
            "series": [
                sum(1 for v in vulns if v.cvss_score and v.cvss_score >= 9.0),
                sum(1 for v in vulns if v.cvss_score and 7.0 <= v.cvss_score < 9.0),
                sum(1 for v in vulns if v.cvss_score and 4.0 <= v.cvss_score < 7.0),
                sum(1 for v in vulns if v.cvss_score and v.cvss_score < 4.0),
            ],
            "colors": ["#dc2626", "#f97316", "#eab308", "#6b7280"],
        }

    async def get_trends(self, user_id: Optional[int] = None) -> dict:
        from sqlalchemy.orm import selectinload
        audit_query = select(Auditoria).options(selectinload(Auditoria.vulnerabilidades)).order_by(Auditoria.created_at.asc())
        if user_id:
            audit_query = audit_query.where(Auditoria.user_id == user_id)

        audits = (await self.db.execute(audit_query)).scalars().all()

        trends = {}
        for audit in audits:
            date_key = audit.created_at.strftime("%Y-%m-%d") if audit.created_at else "unknown"
            if date_key not in trends:
                trends[date_key] = {"audits": 0, "vulnerabilities": 0}
            trends[date_key]["audits"] += 1
            trends[date_key]["vulnerabilities"] += len(audit.vulnerabilidades)

        return {
            "dates": list(trends.keys()),
            "audits": [t["audits"] for t in trends.values()],
            "vulnerabilities": [t["vulnerabilities"] for t in trends.values()],
        }

    async def get_compliance_radar(self) -> dict:
        return {
            "labels": ["OWASP Top 10", "NIST CSF", "NIST 800-82", "ISO 27001", "CIS Controls", "MITRE ATT&CK"],
            "scores": [45, 30, 15, 28, 25, 8],
            "max_score": 100,
        }

    def _calculate_compliance_score(self, vulns: list) -> float:
        if not vulns:
            return 100.0
        critical_count = sum(1 for v in vulns if v.cvss_score and v.cvss_score >= 9.0)
        resolved_count = sum(1 for v in vulns if v.resuelta == "completada")
        score = 100 - (critical_count * 10) - (len(vulns) - resolved_count) * 2
        return max(0, min(100, score))
