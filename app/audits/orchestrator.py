import os
import shutil
import tempfile
import hashlib
import asyncio
import datetime
import logging
from urllib.parse import urlparse
from git import Repo
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from app.projects.models import Proyecto, ArchivoProyecto
from app.projects.service import ProjectService
from app.projects.detector import LanguageDetector
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
    ("git_clone", "Clonando repositorio"),
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
        import json
        progress = {
            "percentage": percentage,
            "steps": steps,
            "message": message,
            "vulnerabilities_found": vulns_found,
        }
        audit.resultado_resumen = {"progress": progress}
        await self.db.execute(
            text("UPDATE sc_auditorias SET resultado_resumen = :val WHERE id = :id"),
            {"val": json.dumps(audit.resultado_resumen), "id": audit.id},
        )
        await self.db.commit()

    @staticmethod
    def _build_auth_url(git_url: str, username: str, token: str) -> str:
        if not token:
            return git_url
        parsed = urlparse(git_url)
        if parsed.scheme != "https":
            return git_url
        auth_netloc = f"{username}:{token}@{parsed.hostname}"
        if parsed.port:
            auth_netloc += f":{parsed.port}"
        return parsed._replace(netloc=auth_netloc).geturl()

    async def _clone_and_load_files(self, audit: Auditoria, project: Proyecto) -> list[ArchivoProyecto]:
        existing = await self.project_service.get_project_files(project.id)
        if existing:
            return existing

        git_url = audit.git_url
        if not git_url:
            return []

        auth_url = self._build_auth_url(git_url, audit.git_username or "", audit.git_token or "")

        loop = asyncio.get_event_loop()
        clone_dir = tempfile.mkdtemp(prefix=f"sc_clone_{project.id}_")
        try:
            log_url = git_url.split("@")[-1] if "@" in git_url else git_url
            logger.info(f"Clonando {log_url} en {clone_dir}")
            await loop.run_in_executor(None, lambda: Repo.clone_from(auth_url, clone_dir, depth=1))

            if audit.git_token:
                audit.git_token = None
                await self.db.commit()

            detector = LanguageDetector()
            created = []
            for root, dirs, filenames in os.walk(clone_dir):
                dirs[:] = [d for d in dirs if d != '.git']
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    try:
                        with open(full_path, 'rb') as f:
                            raw = f.read()
                        text = raw.decode('utf-8', errors='replace')
                    except Exception:
                        continue
                    rel_path = os.path.relpath(full_path, clone_dir)
                    file_hash = hashlib.sha256(raw).hexdigest()
                    lenguaje = detector.detect_language(rel_path)
                    MAX_BYTES = 65000
                    encoded = text.encode('utf-8')[:MAX_BYTES]
                    contenido = encoded.decode('utf-8', errors='replace')
                    archivo = ArchivoProyecto(
                        proyecto_id=project.id,
                        ruta=rel_path.replace("\\", "/"),
                        hash=file_hash,
                        tamano=len(raw),
                        lenguaje=lenguaje,
                        contenido=contenido,
                    )
                    self.db.add(archivo)
                    created.append(archivo)

            if created:
                project.lenguaje = detector.detect_project_language(created)
                project.framework = detector.detect_framework(clone_dir)
                project.estado = "en_revision"

            await self.db.commit()
            logger.info(f"Clonado completado: {len(created)} archivos")
            return created

        except Exception as e:
            logger.exception("Error clonando repositorio")
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise
        finally:
            shutil.rmtree(clone_dir, ignore_errors=True)

    async def run_audit(self, audit: Auditoria) -> dict:
        logger.info(f"Iniciando auditoría {audit.id} para proyecto {audit.proyecto_id}")
        audit.estado = "ejecutando"
        await self.db.commit()

        try:
            project = await self.project_service.get_project(audit.proyecto_id)

            total_steps = len(WORKER_STEPS) + len(EXTRA_STEPS)
            steps_status = []
            for _, label in WORKER_STEPS:
                steps_status.append({"name": label, "status": "pendiente"})
            for _, label in EXTRA_STEPS:
                steps_status.append({"name": label, "status": "pendiente"})

            # Step 0: Clone repo if needed (index 0 in EXTRA_STEPS)
            w = len(WORKER_STEPS)  # clone step is at index n_workers
            steps_status[w]["status"] = "ejecutando"
            await self._update_progress(audit, 0, steps_status, "Clonando repositorio...")
            files = await self._clone_and_load_files(audit, project)
            steps_status[w]["status"] = "completado"
            steps_status[w]["files_count"] = len(files)
            await self._update_progress(audit, 2, steps_status, f"Clonado: {len(files)} archivos cargados", 0)

            if not files:
                raise Exception("No se encontraron archivos para analizar. Verifica que el repositorio contenga código fuente.")

            all_vulns = []
            for i, (worker_cls, label) in enumerate(WORKER_STEPS):
                worker = self.workers[i]
                steps_status[i]["status"] = "ejecutando"
                pct = int((i / total_steps) * 98) + 2
                await self._update_progress(
                    audit, pct, steps_status,
                    f"Escaneando: {label}", len(all_vulns),
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
                        audit, pct, steps_status,
                        f"✓ {label}: {len(vulns)} vulnerabilidades encontradas",
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
                        audit, pct, steps_status,
                        f"✗ {label}: {str(e)[:80]}",
                        len(all_vulns),
                    )

            n_workers = len(WORKER_STEPS)
            n_extra = len(EXTRA_STEPS)
            ai_idx = w + 1
            comp_idx = w + 2
            agg_idx = w + 3

            ai_analysis = {"analysis": [], "action_plan": {}}
            compliance_results = {"overall_score": 0}
            risk_scores = {}
            vulnerabilities = []

            if ai_idx < n_workers + n_extra:
                steps_status[ai_idx]["status"] = "ejecutando"
                n_vulns = len(all_vulns)

                async def report_ai_progress(idx, total, vtype, archivo):
                    pct = 92 + int((idx / total) * 5)
                    steps_status[ai_idx]["detail"] = f"{vtype} en {archivo}"
                    await self._update_progress(
                        audit, pct, steps_status,
                        f"Analizando con IA ({idx+1}/{total}): {vtype} en {archivo}",
                        n_vulns,
                    )

                await self._update_progress(
                    audit, 92, steps_status,
                    f"Analizando vulnerabilidades con IA (0/{n_vulns})...", n_vulns,
                )
                ai_analysis = await self.ai_analyzer.analyze_vulnerabilities(
                    all_vulns, progress_callback=report_ai_progress,
                )
                steps_status[ai_idx]["status"] = "completado"

            # Compliance
            if comp_idx < n_workers + n_extra:
                steps_status[comp_idx]["status"] = "ejecutando"
                await self._update_progress(
                    audit, 95, steps_status,
                    "Evaluando cumplimiento normativo...", len(all_vulns),
                )
                compliance_results = self.compliance_engine.evaluate(ai_analysis)
                risk_scores = self.risk_calculator.calculate_all(ai_analysis)
                steps_status[comp_idx]["status"] = "completado"

            # Aggregation
            if agg_idx < n_workers + n_extra:
                steps_status[agg_idx]["status"] = "ejecutando"
                await self._update_progress(
                    audit, 98, steps_status,
                    "Guardando resultados...", len(all_vulns),
                )
                vulnerabilities = await self.aggregator.save_results(
                    audit.id, all_vulns, ai_analysis, compliance_results, risk_scores
                )
                steps_status[agg_idx]["status"] = "completado"

            audit.estado = "completada"
            audit.completed_at = datetime.datetime.utcnow()
            audit.resultado_resumen = {
                "reports": {},
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

        except (SQLAlchemyError, Exception) as e:
            logger.exception(f"Error en auditoría {audit.id}")
            try:
                await self.db.rollback()
            except Exception:
                pass
            audit.estado = "fallida"
            raw = audit.resultado_resumen if isinstance(audit.resultado_resumen, dict) else {}
            audit.resultado_resumen = {
                "error": str(e),
                "progress": {
                    "percentage": raw.get("progress", {}).get("percentage", 0) if isinstance(raw, dict) else 0,
                    "steps": raw.get("progress", {}).get("steps", []) if isinstance(raw, dict) else [],
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
