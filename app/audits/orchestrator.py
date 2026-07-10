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
import logging

logger = logging.getLogger("securecode.audit")


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

    async def run_audit(self, audit: Auditoria) -> dict:
        logger.info(f"Iniciando auditoría {audit.id} para proyecto {audit.proyecto_id}")
        audit.estado = "ejecutando"
        await self.db.commit()

        try:
            project = await self.project_service.get_project(audit.proyecto_id)
            files = await self.project_service.get_project_files(audit.proyecto_id)

            total_steps = len(self.workers) + 3
            current_step = 0

            all_results = {}
            worker_tasks = []
            for worker in self.workers:
                task = self._run_worker_safely(worker, audit, project, files)
                worker_tasks.append(task)

            worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)

            vulnerability_results = []
            for worker_name, result in worker_results:
                if isinstance(result, Exception):
                    logger.error(f"Worker {worker_name} failed: {str(result)}")
                    continue
                if result:
                    vulnerability_results.extend(result)

            ai_analysis = await self.ai_analyzer.analyze_vulnerabilities(vulnerability_results)
            compliance_results = self.compliance_engine.evaluate(ai_analysis)
            risk_scores = self.risk_calculator.calculate_all(ai_analysis)

            vulnerabilities = await self.aggregator.save_results(
                audit.id, vulnerability_results, ai_analysis, compliance_results, risk_scores
            )

            audit.estado = "completada"
            audit.resultado_resumen = {
                "total_vulnerabilities": len(vulnerabilities),
                "critical": sum(1 for v in vulnerabilities if v.cvss_score and v.cvss_score >= 9.0),
                "high": sum(1 for v in vulnerabilities if v.cvss_score and 7.0 <= v.cvss_score < 9.0),
                "medium": sum(1 for v in vulnerabilities if v.cvss_score and 4.0 <= v.cvss_score < 7.0),
                "low": sum(1 for v in vulnerabilities if v.cvss_score and v.cvss_score < 4.0),
                "compliance_score": compliance_results.get("overall_score", 0),
            }
            await self.db.commit()

            return audit.resultado_resumen

        except Exception as e:
            logger.exception(f"Error en auditoría {audit.id}")
            audit.estado = "fallida"
            audit.resultado_resumen = {"error": str(e)}
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
