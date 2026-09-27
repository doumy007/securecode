from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.audits.models import Auditoria, Vulnerabilidad
from app.projects.models import Proyecto
from app.auth.models import Usuario
from app.shared.cache import cache
from typing import Optional

# TTL del caché del dashboard: los datos solo cambian cuando el worker
# completa/avanza auditorías (minutos), no en cada página cargada.
DASH_TTL = 60


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
        key = f"dash:kpi:{user_id or 'all'}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Agregaciones SQL: en lugar de cargar TODAS las auditorías y
        # vulnerabilidades a memoria (se degradaba con el volumen), se cuentan
        # por estado y por severidad directamente en la BD.
        audit_query = select(Auditoria.estado, func.count()).group_by(Auditoria.estado)
        if user_id:
            audit_query = audit_query.where(Auditoria.user_id == user_id)
        estado_rows = (await self.db.execute(audit_query)).all()
        estado_counts = {r[0]: (r[1] or 0) for r in estado_rows}

        vuln_query = select(
            func.count(Vulnerabilidad.id),
            func.coalesce(func.sum(case((Vulnerabilidad.cvss_score >= 9.0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((and_(Vulnerabilidad.cvss_score >= 7.0, Vulnerabilidad.cvss_score < 9.0), 1), else_=0)), 0),
            func.coalesce(func.sum(case((and_(Vulnerabilidad.cvss_score >= 4.0, Vulnerabilidad.cvss_score < 7.0), 1), else_=0)), 0),
            func.coalesce(func.sum(case((and_(Vulnerabilidad.cvss_score >= 0.0, Vulnerabilidad.cvss_score < 4.0), 1), else_=0)), 0),
            func.coalesce(func.sum(case((Vulnerabilidad.resuelta == "completada", 1), else_=0)), 0),
        ).join(Auditoria, Vulnerabilidad.auditoria_id == Auditoria.id)
        if user_id:
            vuln_query = vuln_query.where(Auditoria.user_id == user_id)
        result = await self.db.execute(vuln_query)
        total_vulns, critical, high, medium, low, resolved = result.one()

        proyectos = (await self.db.execute(select(func.count()).select_from(Proyecto))).scalar()
        usuarios = (await self.db.execute(select(func.count()).select_from(Usuario))).scalar()

        result = {
            "total_proyectos": proyectos or 0,
            "total_auditorias": sum(estado_counts.values()),
            "total_vulnerabilidades": int(total_vulns or 0),
            "total_usuarios": usuarios or 0,
            "completed_audits": estado_counts.get("completada", 0),
            "failed_audits": estado_counts.get("fallida", 0),
            "critical": int(critical or 0),
            "high": int(high or 0),
            "medium": int(medium or 0),
            "low": int(low or 0),
            "resolved": int(resolved or 0),
            "compliance_score": self._calculate_compliance_score(
                total_vulns, critical, resolved
            ),
        }
        cache.set(key, result, ttl_seconds=DASH_TTL)
        return result

    async def get_vulnerability_by_severity(self, user_id: Optional[int] = None) -> dict:
        key = f"dash:severity:{user_id or 'all'}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        vuln_query = select(
            func.coalesce(func.sum(case((Vulnerabilidad.cvss_score >= 9.0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((and_(Vulnerabilidad.cvss_score >= 7.0, Vulnerabilidad.cvss_score < 9.0), 1), else_=0)), 0),
            func.coalesce(func.sum(case((and_(Vulnerabilidad.cvss_score >= 4.0, Vulnerabilidad.cvss_score < 7.0), 1), else_=0)), 0),
            func.coalesce(func.sum(case((and_(Vulnerabilidad.cvss_score >= 0.0, Vulnerabilidad.cvss_score < 4.0), 1), else_=0)), 0),
        ).join(Auditoria, Vulnerabilidad.auditoria_id == Auditoria.id)
        if user_id:
            vuln_query = vuln_query.where(Auditoria.user_id == user_id)
        critical, high, medium, low = (await self.db.execute(vuln_query)).one()

        counts = [int(critical or 0), int(high or 0), int(medium or 0), int(low or 0)]
        result = {
            "critical": counts[0],
            "high": counts[1],
            "medium": counts[2],
            "low": counts[3],
            "labels": ["Crítica", "Alta", "Media", "Baja"],
            "series": counts,
            "colors": ["#dc2626", "#f97316", "#eab308", "#6b7280"],
        }
        cache.set(key, result, ttl_seconds=DASH_TTL)
        return result

    async def get_trends(self, user_id: Optional[int] = None) -> dict:
        key = f"dash:trends:{user_id or 'all'}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Auditorías y vulnerabilidades agrupadas por día en BD (1 query c/u)
        # en lugar de cargar todas las auditorías + sus vulns a memoria.
        date_col = func.date(Auditoria.created_at)
        audit_query = (
            select(date_col.label("d"), func.count().label("c"))
            .where(Auditoria.created_at.is_not(None))
            .group_by(date_col)
            .order_by(date_col)
        )
        vuln_query = (
            select(date_col.label("d"), func.count(Vulnerabilidad.id).label("c"))
            .join(Auditoria, Vulnerabilidad.auditoria_id == Auditoria.id)
            .where(Auditoria.created_at.is_not(None))
            .group_by(date_col)
            .order_by(date_col)
        )
        if user_id:
            audit_query = audit_query.where(Auditoria.user_id == user_id)
            vuln_query = vuln_query.where(Auditoria.user_id == user_id)

        audit_rows = (await self.db.execute(audit_query)).all()
        vuln_rows = (await self.db.execute(vuln_query)).all()

        vuln_counts = {str(r.d): (r.c or 0) for r in vuln_rows}
        dates = [str(r.d) for r in audit_rows]
        audits = [r.c or 0 for r in audit_rows]
        vulnerabilities = [vuln_counts.get(d, 0) for d in dates]

        result = {
            "dates": dates,
            "audits": audits,
            "vulnerabilities": vulnerabilities,
        }
        cache.set(key, result, ttl_seconds=DASH_TTL)
        return result

    async def get_vulnerabilities_by_project(self, user_id: Optional[int] = None) -> list:
        key = f"dash:byproject:{user_id or 'all'}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Vulnerabilidades por proyecto en una sola agregación SQL (LEFT JOIN
        # para incluir proyectos sin vulnerabilidades con total 0), ordenado
        # de mayor a menor. OJO: el filtro por usuario va dentro de la JOIN,
        # no en WHERE, para no descartar proyectos sin auditorías del usuario.
        # No-admin: el filtro de auditorías va DENTRO de la JOIN (para no
        # descartar proyectos sin auditorías del usuario) y además se limita
        # a sus propios proyectos, igual que el endpoint /projects.
        audit_cond = Auditoria.proyecto_id == Proyecto.id
        if user_id:
            audit_cond = and_(audit_cond, Auditoria.user_id == user_id)
        query = (
            select(Proyecto.id, Proyecto.nombre, func.count(Vulnerabilidad.id).label("total"))
            .select_from(Proyecto)
            .outerjoin(Auditoria, audit_cond)
            .outerjoin(Vulnerabilidad, Vulnerabilidad.auditoria_id == Auditoria.id)
            .group_by(Proyecto.id, Proyecto.nombre)
            .order_by(func.count(Vulnerabilidad.id).desc())
        )
        if user_id:
            query = query.where(Proyecto.user_id == user_id)
        rows = (await self.db.execute(query)).all()
        result = [
            {"id": r.id, "nombre": r.nombre, "total": int(r.total or 0)}
            for r in rows
        ]
        cache.set(key, result, ttl_seconds=DASH_TTL)
        return result

    async def get_compliance_radar(self) -> dict:
        return {
            "labels": ["OWASP Top 10", "NIST CSF", "NIST 800-82", "ISO 27001", "CIS Controls", "MITRE ATT&CK"],
            "scores": [45, 30, 15, 28, 25, 8],
            "max_score": 100,
        }

    def _calculate_compliance_score(self, total_vulns, critical_count, resolved_count) -> float:
        if not total_vulns:
            return 100.0
        score = 100 - (int(critical_count or 0) * 10) - (int(total_vulns) - int(resolved_count or 0)) * 2
        return max(0, min(100, score))
