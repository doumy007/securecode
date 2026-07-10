from app.workers.base import BaseWorker
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto
import logging

logger = logging.getLogger("securecode.workers")


CVE_DATABASE = {
    "spring-boot": {
        "2.5": [{"id": "CVE-2024-22262", "severity": "CRITICAL", "cvss": 9.8, "desc": "Spring Boot Actuator improper authorization"}],
        "2.6": [{"id": "CVE-2024-22262", "severity": "HIGH", "cvss": 7.5, "desc": "Spring Boot Actuator improper authorization"}],
        "2.7": [{"id": "CVE-2023-34055", "severity": "HIGH", "cvss": 7.5, "desc": "Spring Boot Jersey bypass"}],
    },
    "log4j": {
        "2.0": [{"id": "CVE-2021-45046", "severity": "CRITICAL", "cvss": 9.0, "desc": "Log4j JNDI injection - DoS"}],
        "2.14": [{"id": "CVE-2021-44228", "severity": "CRITICAL", "cvss": 10.0, "desc": "Log4j JNDI injection - RCE"}],
        "2.15": [{"id": "CVE-2021-45046", "severity": "HIGH", "cvss": 7.5, "desc": "Log4j JNDI injection - DoS"}],
    },
    "jackson-databind": {
        "2.12": [{"id": "CVE-2022-42003", "severity": "HIGH", "cvss": 7.5, "desc": "Jackson DoS via deeply nested objects"}],
        "2.13": [{"id": "CVE-2022-42004", "severity": "HIGH", "cvss": 7.5, "desc": "Jackson DoS via deeply nested objects"}],
    },
    "lodash": {
        "4.17.20": [{"id": "CVE-2021-23337", "severity": "HIGH", "cvss": 7.4, "desc": "Lodash prototype pollution"}],
        "4.17.21": [{"id": "CVE-2024-23337", "severity": "HIGH", "cvss": 7.3, "desc": "Lodash prototype pollution vulnerability"}],
    },
    "express": {
        "4.17": [{"id": "CVE-2022-24999", "severity": "MEDIUM", "cvss": 5.3, "desc": "Express open redirect"}],
    },
    "requests": {
        "2.28": [{"id": "CVE-2023-32681", "severity": "MEDIUM", "cvss": 6.1, "desc": "Requests certificate check bypass"}],
    },
    "django": {
        "3.2": [{"id": "CVE-2024-24680", "severity": "HIGH", "cvss": 7.5, "desc": "Django denial-of-service via zipfile"}],
        "4.0": [{"id": "CVE-2023-31047", "severity": "MEDIUM", "cvss": 5.5, "desc": "Django file upload path traversal"}],
    },
}


class DependencyCheckWorker(BaseWorker):
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        logger.info(f"DependencyCheckWorker: Analizando dependencias del proyecto {project.id}")
        vulnerabilities = []

        deps = self._extract_all_dependencies(files)
        for dep in deps:
            cves = self._check_cve(dep["name"], dep["version"])
            for cve in cves:
                vulnerabilities.append({
                    "tipo": "CVE",
                    "nombre": f"CVE: {dep['name']} {dep['version']} - {cve['id']}",
                    "descripcion": cve["desc"],
                    "severidad": cve["severity"].lower(),
                    "cvss_score": cve["cvss"],
                    "linea_inicio": 0, "linea_fin": 0,
                    "codigo_vulnerable": f"Dependencia: {dep['name']}@{dep['version']}",
                    "codigo_corregido": f"Actualizar {dep['name']} a la versión más reciente",
                    "recomendacion": f"Actualizar {dep['name']} a una versión parcheada. CVE: {cve['id']} - {cve['desc']}",
                    "fuente": "DependencyCheck",
                    "archivo_ruta": dep.get("file", ""),
                })

        logger.info(f"DependencyCheckWorker: {len(vulnerabilities)} CVEs encontrados")
        return self._build_result(vulnerabilities)

    def _extract_all_dependencies(self, files: list[ArchivoProyecto]) -> list:
        deps = []
        import re

        for f in files:
            if not f.contenido:
                continue

            if f.ruta.endswith("pom.xml"):
                pom_deps = re.findall(r"<artifactId>([^<]+)</artifactId>.*?<version>([^<]+)</version>", f.contenido, re.DOTALL)
                for art, ver in pom_deps:
                    deps.append({"name": art.lower(), "version": ver, "file": f.ruta})

            elif f.ruta.endswith("package.json"):
                import json
                try:
                    data = json.loads(f.contenido)
                    for dep_type in ["dependencies", "devDependencies"]:
                        for name, version in data.get(dep_type, {}).items():
                            clean_ver = version.replace("^", "").replace("~", "")
                            deps.append({"name": name.lower(), "version": clean_ver, "file": f.ruta})
                except Exception:
                    pass

            elif f.ruta.endswith("requirements.txt"):
                for line in f.contenido.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        parts = line.split("==")
                        deps.append({"name": parts[0].lower(), "version": parts[1] if len(parts) > 1 else "latest", "file": f.ruta})

            elif f.ruta.endswith("build.gradle"):
                gradle_deps = re.findall(r"(implementation|api)\s+['\"]([^:]+):([^:]+):([^'\"]+)['\"]", f.contenido)
                for _, group, artifact, version in gradle_deps:
                    deps.append({"name": f"{group}:{artifact}".lower(), "version": version, "file": f.ruta})

            elif f.ruta.endswith("go.mod"):
                for line in f.contenido.split("\n"):
                    parts = line.strip().split()
                    if len(parts) >= 2 and not line.startswith("go ") and not line.startswith("module ") and not line.startswith("require"):
                        deps.append({"name": parts[0].lower(), "version": parts[1], "file": f.ruta})

        return deps

    def _check_cve(self, dep_name: str, dep_version: str) -> list:
        findings = []
        for lib, versions in CVE_DATABASE.items():
            if lib in dep_name:
                for ver, cves in versions.items():
                    if self._version_matches(dep_version, ver):
                        findings.extend(cves)
        return findings

    def _version_matches(self, dep_ver: str, cve_ver: str) -> bool:
        if dep_ver.startswith(cve_ver):
            return True
        if dep_ver == cve_ver:
            return True
        try:
            dep_parts = [int(x) for x in dep_ver.split(".")]
            cve_parts = [int(x) for x in cve_ver.split(".")]
            for i in range(min(len(dep_parts), len(cve_parts))):
                if dep_parts[i] < cve_parts[i]:
                    return False
            return True
        except Exception:
            return False
