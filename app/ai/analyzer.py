import asyncio
import logging
from app.ai.openai_client import OpenAIClient
from app.ai.prompts import ACTION_PLAN_PROMPT, COMBINED_ANALYSIS_PROMPT, FRAMEWORK_REPORT_PROMPTS
from typing import Optional, Callable

logger = logging.getLogger("securecode.ai")


class AIAnalyzer:
    def __init__(self):
        self.client = OpenAIClient()
        self._semaphore = asyncio.Semaphore(4)

    async def analyze_vulnerabilities(self, findings: list,
                                       progress_callback: Optional[Callable] = None) -> dict:
        if not findings:
            return {"analysis": [], "action_plan": {}}

        total = len(findings)
        seen_types = set()

        async def process_one(idx, finding):
            vuln_type = finding.get("tipo", "unknown")
            archivo = finding.get("archivo", finding.get("ruta", ""))
            if progress_callback:
                await progress_callback(idx, total, vuln_type, archivo)
            async with self._semaphore:
                result = await self.client.combined_analysis(finding)
            analysis = result.get("analysis", {})
            finding["codigo_corregido"] = result.get("codigo_corregido", "")
            compliance = result.get("compliance", {"mapeos": []})
            return analysis, compliance, vuln_type

        tasks = [process_one(i, f) for i, f in enumerate(findings)]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        results = {"analysis": [], "action_plan": {}, "compliance": []}
        for out in outputs:
            if isinstance(out, Exception):
                logger.error(f"Error analyzing finding: {out}")
                continue
            analysis, compliance, vuln_type = out
            results["analysis"].append(analysis)
            results["compliance"].append(compliance)
            if vuln_type not in seen_types:
                seen_types.add(vuln_type)
                plan = await self._generate_action_plan(vuln_type)
                if plan:
                    results["action_plan"][vuln_type] = plan

        return results

    async def generate_framework_report(self, framework: str, audit_info: dict,
                                          findings: list, project_info: dict) -> dict:
        prompt = FRAMEWORK_REPORT_PROMPTS.get(framework)
        if not prompt:
            raise ValueError(f"Framework desconocido: {framework}")

        findings_summary = []
        for f in findings[:30]:
            findings_summary.append({
                "tipo": f.get("tipo", "unknown"),
                "archivo": f.get("archivo", f.get("ruta", "")),
                "linea_inicio": f.get("linea_inicio"),
                "linea_fin": f.get("linea_fin"),
                "descripcion": f.get("descripcion", ""),
                "severidad": f.get("severidad", "media"),
                "cvss_score": f.get("cvss_score"),
                "codigo_vulnerable": f.get("codigo_vulnerable", "")[:1000],
                "codigo_corregido": f.get("codigo_corregido", "")[:1000],
                "recomendacion": f.get("recomendacion", ""),
                "mapeos": f.get("mapeos", []),
            })

        context = {
            "project": project_info,
            "audit": audit_info,
            "findings": findings_summary,
            "total_findings": len(findings),
        }

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"""
Genera el informe de cumplimiento para el framework {framework}.

DATOS DE LA AUDITORÍA:
- Proyecto: {project_info.get('nombre', 'N/A')}
- Auditoría ID: {audit_info.get('id', 'N/A')}
- Fecha: {audit_info.get('fecha', 'N/A')}
- Total hallazgos: {len(findings)}

HALLAZGOS A EVALUAR (máximo 30 mostrados):
{findings_summary}

Genera el JSON completo del informe según las instrucciones del framework.
"""},
        ]

        try:
            result = await self.client.chat_completion(messages)
            report = self.client._parse_json_response(result)
            report["report_metadata"] = {
                "framework": framework,
                "generated_at": audit_info.get("fecha", ""),
                "author": "SecureCode AI Auditor",
                "project_name": project_info.get("nombre", ""),
                "audit_id": audit_info.get("id"),
            }
            return report
        except Exception as e:
            logger.error(f"Error generando reporte {framework}: {e}")
            return {
                "report_metadata": {"framework": framework, "error": str(e)},
                "executive_summary": {"overview": f"Error generando reporte: {e}", "compliance_score": 0},
                "controls_evaluation": [],
                "findings": [],
                "implementation_plan": [],
                "compliance_summary": {"current_score": 0},
                "developer_checklist": [],
            }

    async def _generate_action_plan(self, vuln_type: str) -> list:
        try:
            messages = [
                {"role": "system", "content": ACTION_PLAN_PROMPT},
                {"role": "user", "content": f"Genera plan de acci\u00f3n para vulnerabilidades tipo: {vuln_type}"},
            ]
            result = await self.client.chat_completion(messages)
            return self.client._parse_json_response(result).get("plan", [])
        except Exception as e:
            logger.error(f"Error generating action plan for {vuln_type}: {e}")
            return []
