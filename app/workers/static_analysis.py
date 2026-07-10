from app.workers.base import BaseWorker
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto
import logging
import re

logger = logging.getLogger("securecode.workers")


class StaticAnalysisWorker(BaseWorker):
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        logger.info(f"StaticAnalysisWorker: Analizando código del proyecto {project.id}")
        vulnerabilities = []

        for f in files:
            if not f.contenido or not f.lenguaje:
                continue

            lang = f.lenguaje.lower()
            if "java" in lang:
                findings = self._analyze_java(f.ruta, f.contenido)
            elif "python" in lang:
                findings = self._analyze_python(f.ruta, f.contenido)
            elif "javascript" in lang or "typescript" in lang:
                findings = self._analyze_javascript(f.ruta, f.contenido)
            elif "go" in lang:
                findings = self._analyze_go(f.ruta, f.contenido)
            else:
                findings = []

            vulnerabilities.extend(findings)

        logger.info(f"StaticAnalysisWorker: {len(vulnerabilities)} hallazgos")
        return self._build_result(vulnerabilities)

    def _analyze_java(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "catch (Exception e)" in line or "catch (Throwable t)" in line:
                if any(kw in line for kw in ["printStackTrace", "e.printStackTrace", "System.out"]):
                    findings.append(self._finding(filepath, i, "Poor Error Handling",
                        "Manejo de errores inadecuado: imprimir stack trace en stdout",
                        "media", 5.0, line.strip(), "Usar logger.error() en lugar de printStackTrace()"))

            if "String" in line and "password" in line.lower() and "=" in line:
                findings.append(self._finding(filepath, i, "String for Password",
                    "Se usa String para contraseñas - no borrable de memoria",
                    "media", 5.5, line.strip(), "Usar char[] o SecretBytes para almacenar contraseñas"))

            if "Thread.sleep" in line and "controller" in filepath.lower():
                findings.append(self._finding(filepath, i, "Thread.sleep in Controller",
                    "Thread.sleep() en controller puede degradar rendimiento",
                    "baja", 3.0, line.strip(), "Usar CompletableFuture o mecanismos async"))

            if "System.getenv" in line and "password" in line.lower():
                findings.append(self._finding(filepath, i, "Potential Secret Exposure",
                    "Posible exposición de secretos via variables de entorno en logs",
                    "media", 4.5, line.strip(), "Usar @Value o Vault para inyectar secretos"))

        return findings

    def _analyze_python(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "eval(" in line or "exec(" in line:
                findings.append(self._finding(filepath, i, "Dynamic Code Execution",
                    "Uso de eval()/exec() permite ejecución de código arbitrario",
                    "crítica", 9.0, line.strip(), "Evitar eval/exec. Usar ast.literal_eval() si es necesario"))

            if "pickle.loads" in line or "pickle.load(" in line:
                findings.append(self._finding(filepath, i, "Insecure Deserialization",
                    "pickle es inseguro para datos no confiables",
                    "crítica", 9.0, line.strip(), "Usar JSON en lugar de pickle para datos externos"))

            if "assert " in line and not "#" in line.split("assert")[1]:
                if len(line.strip()) > 20:
                    findings.append(self._finding(filepath, i, "Assert Used for Validation",
                        "assert es deshabilitable con -O. Usar if/raise para validación",
                        "alta", 7.0, line.strip(), "Reemplazar assert por if condition: raise ValueError()"))

            if "input(" in line and "password" in line.lower():
                pass

            if "print(" in line and "password" in line.lower():
                findings.append(self._finding(filepath, i, "Potential Password Leak",
                    "Posible fuga de contraseña en consola",
                    "alta", 7.0, line.strip(), "No imprimir contraseñas en logs o consola"))

        return findings

    def _analyze_javascript(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "localStorage" in line and ("token" in line.lower() or "jwt" in line.lower() or "password" in line.lower()):
                findings.append(self._finding(filepath, i, "Sensitive Data in localStorage",
                    "Datos sensibles almacenados en localStorage - vulnerable a XSS",
                    "alta", 7.0, line.strip(), "Usar httpOnly cookies para tokens JWT"))

            if "innerHTML" in line and ("+" in line or "concat" in line):
                findings.append(self._finding(filepath, i, "XSS via innerHTML",
                    "Inserción de HTML no sanitizado vulnerable a XSS",
                    "alta", 7.5, line.strip(), "Usar textContent o sanitizar con DOMPurify"))

            if "console.log" in line and any(kw in line.lower() for kw in ["password", "token", "secret", "key"]):
                findings.append(self._finding(filepath, i, "Sensitive Data in Console",
                    "Datos sensibles en console.log - posible exposición",
                    "media", 5.0, line.strip(), "Eliminar console.log de datos sensibles antes de producción"))

            if "==" in line and not "===" in line:
                if any(kw in line for kw in ["if", "return", "while", "?"]):
                    findings.append(self._finding(filepath, i, "Type Coercion (==)",
                        "Uso de == en lugar de === puede causar comparaciones inesperadas",
                        "baja", 3.0, line.strip(), "Usar === en lugar de == para comparaciones estrictas"))

        return findings

    def _analyze_go(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "sql.Query" in line and "fmt.Sprintf" in line:
                findings.append(self._finding(filepath, i, "SQL Injection Risk",
                    "Posible inyección SQL: concatenación de queries con Sprintf",
                    "crítica", 9.8, line.strip(), "Usar parámetros posicionales en Queries"))

            for kw in ["secret", "password", "apikey", "api_key", "token"]:
                if kw in line.lower() and "=" in line and not "os.Getenv" in line and not "viper" in line:
                    findings.append(self._finding(filepath, i, "Hardcoded Credential",
                        f"Posible {kw} hardcodeado en el código",
                        "alta", 7.5, line.strip(), f"Usar variables de entorno o vault para {kw}"))

        return findings

    def _finding(self, filepath: str, line: int, vuln_type: str, desc: str,
                 severity: str, cvss: float, code: str, recommendation: str) -> dict:
        return {
            "tipo": vuln_type,
            "nombre": vuln_type,
            "descripcion": desc,
            "severidad": severity,
            "cvss_score": cvss,
            "linea_inicio": line, "linea_fin": line,
            "codigo_vulnerable": code,
            "codigo_corregido": "",
            "recomendacion": recommendation,
            "fuente": "StaticAnalysis",
            "archivo_ruta": filepath,
        }
