from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.audits.models import Vulnerabilidad, MapeoEstandar, TareaRemediacion, Auditoria
from app.projects.models import ArchivoProyecto
import logging
from typing import Optional

logger = logging.getLogger("securecode.workers")


class ResultAggregator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_results(
        self,
        audit_id: int,
        worker_findings: list,
        ai_analysis: dict,
        compliance_results: dict,
        risk_scores: dict,
    ) -> list[Vulnerabilidad]:
        saved_vulns = []

        for finding in worker_findings:
            archivo = None
            if finding.get("archivo_ruta"):
                result = await self.db.execute(
                    select(ArchivoProyecto).where(
                        ArchivoProyecto.proyecto_id == (
                            select(Auditoria.proyecto_id).where(Auditoria.id == audit_id).scalar_subquery()
                        ),
                        ArchivoProyecto.ruta == finding["archivo_ruta"],
                    )
                )
                archivo = result.scalar_one_or_none()

            vuln = Vulnerabilidad(
                auditoria_id=audit_id,
                archivo_id=archivo.id if archivo else None,
                tipo=finding.get("tipo", "Unknown"),
                nombre=finding.get("nombre", "Unknown Vulnerability"),
                descripcion=finding.get("descripcion", ""),
                severidad=finding.get("severidad", "media"),
                cvss_score=finding.get("cvss_score"),
                impacto=risk_scores.get(finding.get("tipo", ""), {}).get("impacto"),
                probabilidad=risk_scores.get(finding.get("tipo", ""), {}).get("probabilidad"),
                prioridad=finding.get("prioridad"),
                linea_inicio=finding.get("linea_inicio"),
                linea_fin=finding.get("linea_fin"),
                codigo_vulnerable=finding.get("codigo_vulnerable", ""),
                codigo_corregido=finding.get("codigo_corregido", ""),
                recomendacion=finding.get("recomendacion", ""),
                fuente=finding.get("fuente", "Unknown"),
            )
            self.db.add(vuln)
            await self.db.flush()

            vuln_type = finding.get("tipo", "")
            if vuln_type in compliance_results:
                for std_entry in compliance_results[vuln_type]:
                    mapeo = MapeoEstandar(
                        vulnerabilidad_id=vuln.id,
                        estandar=std_entry.get("estandar", ""),
                        categoria=std_entry.get("categoria", ""),
                        referencia=std_entry.get("referencia", ""),
                        descripcion=std_entry.get("descripcion", ""),
                    )
                    self.db.add(mapeo)

            action_plan = ai_analysis.get("action_plan", {}).get(vuln_type, [])
            for step_num, step in enumerate(action_plan, 1):
                tarea = TareaRemediacion(
                    auditoria_id=audit_id,
                    vulnerabilidad_id=vuln.id,
                    paso=step_num,
                    descripcion=step.get("descripcion", ""),
                    archivo=finding.get("archivo_ruta"),
                    metodo=step.get("metodo", ""),
                    prioridad=finding.get("severidad", "media"),
                )
                self.db.add(tarea)

            saved_vulns.append(vuln)

        await self.db.commit()
        logger.info(f"Guardadas {len(saved_vulns)} vulnerabilidades para auditoría {audit_id}")
        return saved_vulns
