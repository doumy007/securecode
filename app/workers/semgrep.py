from app.workers.base import BaseWorker
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto
import logging
import re

logger = logging.getLogger("securecode.workers")


class SemgrepWorker(BaseWorker):
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        logger.info(f"SemgrepWorker: Analizando proyecto {project.id}")
        vulnerabilities = []

        for f in files:
            if not f.contenido:
                continue
            findings = self._run_semgrep_rules(f.ruta, f.contenido)
            vulnerabilities.extend(findings)

        logger.info(f"SemgrepWorker: {len(vulnerabilities)} hallazgos")
        return self._build_result(vulnerabilities)

    def _run_semgrep_rules(self, filepath: str, content: str) -> list:
        findings = []
        findings.extend(self._rule_insecure_crypto(filepath, content))
        findings.extend(self._rule_log_forging(filepath, content))
        findings.extend(self._rule_weak_hash(filepath, content))
        findings.extend(self._rule_xxe(filepath, content))
        findings.extend(self._rule_deserialization(filepath, content))
        findings.extend(self._rule_null_pointer(filepath, content))
        findings.extend(self._rule_open_redirect(filepath, content))
        return findings

    def _rule_insecure_crypto(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in [
                "DES/", "DESede", "RC2", "RC4", "Blowfish",
                "AES/ECB", "PBEWithMD5", "PBEWithSHA1",
            ]):
                findings.append({
                    "tipo": "Insecure Cryptography",
                    "nombre": "Uso de algoritmo criptográfico inseguro",
                    "descripcion": "Se utiliza un algoritmo criptográfico débil o modo inseguro (ECB)",
                    "severidad": "alta",
                    "cvss_score": 7.2,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "",
                    "recomendacion": "Usar AES/GCM/NoPadding con IV aleatorio en lugar de ECB",
                    "fuente": "Semgrep", "archivo_ruta": filepath,
                })
        return findings

    def _rule_log_forging(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "log." in line and any(kw in line for kw in ["request", "getParameter", "getQueryString", "input"]):
                findings.append({
                    "tipo": "Log Forging",
                    "nombre": "Posible log forging con entrada del usuario",
                    "descripcion": "Se registra información no sanitizada del usuario en logs",
                    "severidad": "media",
                    "cvss_score": 5.3,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "",
                    "recomendacion": "Sanitizar y limitar la longitud de entradas de usuario en logs. Usar un logger CRLF-safe",
                    "fuente": "Semgrep", "archivo_ruta": filepath,
                })
        return findings

    def _rule_weak_hash(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in ["MD5", "SHA-1", "sha1(", "md5("]):
                findings.append({
                    "tipo": "Weak Hash",
                    "nombre": "Uso de función hash débil",
                    "descripcion": "MD5 y SHA-1 no son seguros criptográficamente",
                    "severidad": "alta",
                    "cvss_score": 7.0,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "",
                    "recomendacion": "Usar SHA-256 o SHA-3 en su lugar. Para contraseñas usar bcrypt/argon2",
                    "fuente": "Semgrep", "archivo_ruta": filepath,
                })
        return findings

    def _rule_xxe(self, filepath: str, content: str) -> list:
        findings = []
        if filepath.endswith(".xml") or filepath.endswith(".java") or filepath.endswith(".py"):
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if any(kw in line for kw in [
                    "DocumentBuilderFactory", "SAXParser", "SAXBuilder",
                    "XMLReader", "DocumentHelper", "SAXReader",
                ]) and "XXE" not in line and any(p in line for p in ["parse", "newInstance", "build"]):
                    findings.append({
                        "tipo": "XML External Entity (XXE)",
                        "nombre": "Posible vulnerabilidad XXE en parser XML",
                        "descripcion": "Parser XML puede permitir entidades externas",
                        "severidad": "alta",
                        "cvss_score": 7.5,
                        "linea_inicio": i, "linea_fin": i,
                        "codigo_vulnerable": line.strip(),
                        "codigo_corregido": "",
                        "recomendacion": "Deshabilitar DOCTYPE y entidades externas: setFeature('http://apache.org/xml/features/disallow-doctype-decl', true)",
                        "fuente": "Semgrep", "archivo_ruta": filepath,
                    })
        return findings

    def _rule_deserialization(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in [
                "ObjectInputStream", "readObject", "pickle.loads",
                "yaml.load(", "yml.load(", "marshal.load",
            ]):
                findings.append({
                    "tipo": "Insecure Deserialization",
                    "nombre": "Deserialización insegura de objetos",
                    "descripcion": "La deserialización de datos no confiables puede permitir ejecución remota de código",
                    "severidad": "crítica",
                    "cvss_score": 9.0,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "",
                    "recomendacion": "Usar JSON en lugar de serialización nativa. Validar y sanitizar datos antes de deserializar",
                    "fuente": "Semgrep", "archivo_ruta": filepath,
                })
        return findings

    def _rule_null_pointer(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "." in line and "return" in line and "get" in line.lower() and "null" not in line.lower():
                if any(kw in line.lower() for kw in ["get", "find", "fetch", "retrieve"]):
                    findings.append({
                        "tipo": "Null Pointer Risk",
                        "nombre": "Posible NullPointerException sin validación",
                        "descripcion": "Se asume que un objeto retornado no es null sin verificar",
                        "severidad": "media",
                        "cvss_score": 5.5,
                        "linea_inicio": i, "linea_fin": i,
                        "codigo_vulnerable": line.strip(),
                        "codigo_corregido": "",
                        "recomendacion": "Agregar validación Optional.isPresent() o if (result != null) antes de usar",
                        "fuente": "Semgrep", "archivo_ruta": filepath,
                    })
        return findings

    def _rule_open_redirect(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if any(kw in line for kw in ["redirect:", "sendRedirect", "redirect(", "Redirect"]) and any(p in line for p in ["param", "request", "input", "url"]):
                findings.append({
                    "tipo": "Open Redirect",
                    "nombre": "Posible open redirect no validado",
                    "descripcion": "Redirección basada en entrada del usuario sin validación de URL de destino",
                    "severidad": "media",
                    "cvss_score": 6.1,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "",
                    "recomendacion": "Validar URLs contra una allowlist. No redirigir basado en parámetros no confiables",
                    "fuente": "Semgrep", "archivo_ruta": filepath,
                })
        return findings
