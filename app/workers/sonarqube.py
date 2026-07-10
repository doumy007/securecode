from app.workers.base import BaseWorker
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto
import logging

logger = logging.getLogger("securecode.workers")


class SonarQubeWorker(BaseWorker):
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        logger.info(f"SonarQubeWorker: Analizando proyecto {project.id}")
        vulnerabilities = []

        for f in files:
            if not f.contenido:
                continue

            content = f.contenido
            findings = self._analyze_content(f.ruta, content)
            vulnerabilities.extend(findings)

        logger.info(f"SonarQubeWorker: {len(vulnerabilities)} hallazgos encontrados")
        return self._build_result(vulnerabilities)

    def _analyze_content(self, filepath: str, content: str) -> list:
        findings = []

        if filepath.endswith(".java") or filepath.endswith(".py") or filepath.endswith(".js"):
            findings.extend(self._check_sql_injection(filepath, content))
            findings.extend(self._check_hardcoded_secrets(filepath, content))
            findings.extend(self._check_xss(filepath, content))
            findings.extend(self._check_command_injection(filepath, content))
            findings.extend(self._check_path_traversal(filepath, content))

        return findings

    def _check_sql_injection(self, filepath: str, content: str) -> list:
        findings = []
        patterns = [
            ("concatena SQL", ["SELECT * FROM", "SELECT ", " FROM ", " WHERE "], ["+", "concat(", "format("]),
            ("PreparedStatement ausente", ["Statement"], []),
            ("JPA query dinámica", ["@Query"], ["+ "]),
        ]
        for vuln_name, include_keywords, specific_patterns in patterns:
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if any(kw in line for kw in include_keywords):
                    if any(p in line for p in specific_patterns):
                        findings.append(self._create_finding(
                            filepath, i, "SQL Injection",
                            "Posible inyección SQL: concatenación de strings en consulta",
                            "CRÍTICA", 9.8,
                            line.strip(),
                            "Usar PreparedStatement o parámetros nombrados",
                        ))
        return findings

    def _check_hardcoded_secrets(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            indicators = ["password", "secret", "api_key", "apikey", "token", "credential", "private_key"]
            if any(ind in line_lower for ind in indicators):
                if "=" in line or ":" in line:
                    value = line.split("=")[-1].split(":")[-1].strip().strip('"').strip("'")
                    if value and not value.startswith("$") and not value.startswith("{") and len(value) > 4:
                        findings.append(self._create_finding(
                            filepath, i, "Hardcoded Secret",
                            "Secreto hardcodeado en el código fuente",
                            "ALTA", 7.5,
                            line.strip(),
                            "Usar variables de entorno o un vault de secrets",
                        ))
        return findings

    def _check_xss(self, filepath: str, content: str) -> list:
        findings = []
        if filepath.endswith(".html") or filepath.endswith(".js") or filepath.endswith(".ts"):
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "innerHTML" in line or "document.write" in line or "dangerouslySetInnerHTML" in line:
                    findings.append(self._create_finding(
                        filepath, i, "Cross-Site Scripting (XSS)",
                        "Posible XSS: inserción directa de HTML sin sanitizar",
                        "ALTA", 7.4,
                        line.strip(),
                        "Usar textContent/innerText o sanitizar con DOMPurify",
                    ))
        return findings

    def _check_command_injection(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in ["Runtime.exec", "ProcessBuilder", "subprocess.call", "exec(", "os.system"]):
                findings.append(self._create_finding(
                    filepath, i, "Command Injection",
                    "Posible inyección de comandos del sistema",
                    "CRÍTICA", 9.3,
                    line.strip(),
                    "Validar y sanitizar entradas, evitar exec() con datos externos",
                ))
        return findings

    def _check_path_traversal(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in ["getResourceAsStream", "File(", "open(", "Path.of"]) and ".." in line:
                findings.append(self._create_finding(
                    filepath, i, "Path Traversal",
                    "Posible path traversal: la entrada del usuario afecta la ruta del archivo",
                    "ALTA", 7.8,
                    line.strip(),
                    "Validar y normalizar rutas, usar allowlist de directorios permitidos",
                ))
        return findings

    def _create_finding(self, filepath: str, line: int, vuln_type: str, desc: str,
                        severity: str, cvss: float, code: str, recommendation: str) -> dict:
        return {
            "tipo": vuln_type,
            "nombre": vuln_type,
            "descripcion": desc,
            "severidad": severity.lower(),
            "cvss_score": cvss,
            "linea_inicio": line,
            "linea_fin": line,
            "codigo_vulnerable": code,
            "codigo_corregido": "",
            "recomendacion": recommendation,
            "fuente": "SonarQube",
            "archivo_ruta": filepath,
        }
