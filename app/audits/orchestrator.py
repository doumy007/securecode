from app.projects.models import Proyecto
from app.projects.service import ProjectService
from app.workers.sonarqube import SonarQubeWorker
from app.workers.semgrep import SemgrepWorker
from app.workers.dependency_check import DependencyCheckWorker
from app.workers.trivy import TrivyWorker
from app.workers.static_analysis import StaticAnalysisWorker
from app.workers.infra_scanner import InfraScannerWorker
from app.workers.result_aggregator import ResultAggregator
from app.ai.analyzer import AIAnalyzer
from app.compliance.engine import ComplianceEngine
from app.compliance.risk_calculator import RiskCalculator
from app.audits.models import Auditoria, ResultadoWorker, Vulnerabilidad
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import asyncio
import datetime
import logging

logger = logging.getLogger("securecode.audit")


WORKER_STEPS = [
    ("SonarQubeWorker", "Análisis SAST (SonarQube)"),
    ("SemgrepWorker", "Análisis de patrones (Semgrep)"),
    ("DependencyCheckWorker", "Verificación de dependencias"),
    ("TrivyWorker", "Escaneo de infraestructura"),
    ("StaticAnalysisWorker", "Análisis estático de código"),
    ("InfraScannerWorker", "Escaneo de IaC"),
]

EXTRA_STEPS = [
    ("ai_analysis", "Análisis con IA"),
    ("compliance", "Evaluación de cumplimiento"),
    ("aggregation", "Generando resultados"),
]


class AuditOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)
        self.ai_analyzer = AIAnalyzer()
        self.compliance_engine = ComplianceEngine()
        self.risk_calculator = RiskCalculator()
        self.aggregator = ResultAggregator(db)
        self.workers = [
            SonarQubeWorker(),
            SemgrepWorker(),
            DependencyCheckWorker(),
            TrivyWorker(),
            StaticAnalysisWorker(),
            InfraScannerWorker(),
        ]

    async def _update_progress(self, audit: Auditoria, percentage: int, steps: list,
                                message: str, vulns_found: int = 0):
        audit.resultado_resumen = audit.resultado_resumen or {}
        audit.resultado_resumen["progress"] = {
            "percentage": percentage,
            "steps": steps,
            "message": message,
            "vulnerabilities_found": vulns_found,
        }
        await self.db.commit()

    async def run_audit(self, audit: Auditoria) -> dict:
        logger.info(f"Iniciando auditoría {audit.id} para proyecto {audit.proyecto_id}")
        audit.estado = "ejecutando"
        await self.db.commit()

        try:
            project = await self.project_service.get_project(audit.proyecto_id)
            files = await self.project_service.get_project_files(audit.proyecto_id)

            total_steps = len(WORKER_STEPS) + len(EXTRA_STEPS)
            steps_status = []
            for _, label in WORKER_STEPS:
                steps_status.append({"name": label, "status": "pendiente"})
            for _, label in EXTRA_STEPS:
                steps_status.append({"name": label, "status": "pendiente"})

            await self._update_progress(audit, 0, steps_status,
                                        "Preparando análisis...")

            all_vulns = []
            for i, (worker_cls, label) in enumerate(WORKER_STEPS):
                worker = self.workers[i]
                steps_status[i]["status"] = "ejecutando"
                await self._update_progress(
                    audit,
                    int((i / total_steps) * 100),
                    steps_status,
                    f"Ejecutando: {label}",
                    len(all_vulns),
                )

                try:
                    result = await worker.run(audit, project, files)
                    vulns = result.get("vulnerabilities", [])
                    all_vulns.extend(vulns)

                    result_worker = ResultadoWorker(
                        auditoria_id=audit.id,
                        worker=worker_cls,
                        estado="completado",
                        resultado=result,
                    )
                    self.db.add(result_worker)
                    await self.db.commit()

                    steps_status[i]["status"] = "completado"
                    steps_status[i]["vulnerabilities"] = len(vulns)
                    await self._update_progress(
                        audit,
                        int(((i + 0.5) / total_steps) * 100),
                        steps_status,
                        f"Completado: {label} ({len(vulns)} vulnerabilidades)",
                        len(all_vulns),
                    )
                except Exception as e:
                    logger.exception(f"Worker {worker_cls} error")

                    result_worker = ResultadoWorker(
                        auditoria_id=audit.id,
                        worker=worker_cls,
                        estado="fallido",
                        resultado={"error": str(e)},
                    )
                    self.db.add(result_worker)
                    await self.db.commit()

                    steps_status[i]["status"] = "fallido"
                    steps_status[i]["error"] = str(e)
                    await self._update_progress(
                        audit,
                        int(((i + 0.5) / total_steps) * 100),
                        steps_status,
                        f"Falló: {label}",
                        len(all_vulns),
                    )

            n_workers = len(WORKER_STEPS)

            steps_status[n_workers]["status"] = "ejecutando"
            await self._update_progress(
                audit,
                int(((n_workers + 0.3) / total_steps) * 100),
                steps_status,
                "Analizando vulnerabilidades con IA...",
                len(all_vulns),
            )
            ai_analysis = await self.ai_analyzer.analyze_vulnerabilities(all_vulns)
            steps_status[n_workers]["status"] = "completado"
            await self._update_progress(
                audit,
                int(((n_workers + 0.6) / total_steps) * 100),
                steps_status,
                "Evaluando cumplimiento normativo...",
                len(all_vulns),
            )

            steps_status[n_workers + 1]["status"] = "ejecutando"
            await self._update_progress(
                audit,
                int(((n_workers + 0.8) / total_steps) * 100),
                steps_status,
                "Calculando riesgos...",
                len(all_vulns),
            )
            compliance_results = self.compliance_engine.evaluate(ai_analysis)
            risk_scores = self.risk_calculator.calculate_all(ai_analysis)
            steps_status[n_workers + 1]["status"] = "completado"

            steps_status[n_workers + 2]["status"] = "ejecutando"
            await self._update_progress(
                audit,
                int(((n_workers + 1) / total_steps) * 100),
                steps_status,
                "Guardando resultados...",
                len(all_vulns),
            )
            vulnerabilities = await self.aggregator.save_results(
                audit.id, all_vulns, ai_analysis, compliance_results, risk_scores
            )
            steps_status[n_workers + 2]["status"] = "completado"

            audit.estado = "completada"
            audit.completed_at = datetime.utcnow()
            audit.resultado_resumen = {
                "total_vulnerabilities": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.cvss_score and v.cvss_score >= 9.0),
                "high": sum(1 for v in vulnerabilities if v.cvss_score and 7.0 <= v.cvss_score < 9.0),
                "medium": sum(1 for v in vulnerabilities if v.cvss_score and 4.0 <= v.cvss_score < 7.0),
                "low": sum(1 for v in vulnerabilities if v.cvss_score and v.cvss_score < 4.0),
                "compliance_score": compliance_results.get("overall_score", 0),
                "progress": {
                    "percentage": 100,
                    "steps": steps_status,
                    "message": "Auditoría completada",
                    "vulnerabilities_found": len(vulnerabilities),
                },
            }
            await self.db.commit()

            return audit.resultado_resumen

        except Exception as e:
            logger.exception(f"Error en auditoría {audit.id}")
            audit.estado = "fallida"
            audit.resultado_resumen = {
                "error": str(e),
                "progress": {
                    "percentage": 100 if "fallida" else audit.resultado_resumen.get("progress", {}).get("percentage", 0),
                    "message": f"Error: {str(e)}",
                    "vulnerabilities_found": 0,
                },
            }
            await self.db.commit()
            raise

    async def _run_worker_safely(self, worker, audit, project, files):
        try:
            worker_name = worker.__class__.__name__
            logger.info(f"Ejecutando worker {worker_name} para auditoría {audit.id}")
            result = await worker.run(audit, project, files)

            result_worker = ResultadoWorker(
                auditoria_id=audit.id,
                worker=worker_name,
                estado="completado",
                resultado=result,
            )
            self.db.add(result_worker)
            await self.db.commit()

            return worker_name, result.get("vulnerabilities", [])
        except Exception as e:
            logger.exception(f"Worker {worker.__class__.__name__} error")
            result_worker = ResultadoWorker(
                auditoria_id=audit.id,
                worker=worker.__class__.__name__,
                estado="fallido",
                resultado={"error": str(e)},
            )
            self.db.add(result_worker)
            await self.db.commit()
            return worker.__class__.__name__, []
