from app.workers.base import BaseWorker
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto
import logging
import re

logger = logging.getLogger("securecode.workers")


class TrivyWorker(BaseWorker):
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        logger.info(f"TrivyWorker: Escaneando infraestructura del proyecto {project.id}")
        vulnerabilities = []

        docker_files = [f for f in files if "Dockerfile" in f.ruta or f.ruta.endswith(".dockerfile")]
        for df in docker_files:
            if df.contenido:
                findings = self._analyze_dockerfile(df.ruta, df.contenido)
                vulnerabilities.extend(findings)

        compose_files = [f for f in files if "docker-compose" in f.ruta]
        for cf in compose_files:
            if cf.contenido:
                findings = self._analyze_compose(cf.ruta, cf.contenido)
                vulnerabilities.extend(findings)

        k8s_files = [f for f in files if f.ruta.endswith(".yaml") or f.ruta.endswith(".yml")]
        for kf in k8s_files:
            if kf.contenido:
                findings = self._analyze_kubernetes(kf.ruta, kf.contenido)
                vulnerabilities.extend(findings)

        logger.info(f"TrivyWorker: {len(vulnerabilities)} hallazgos de infraestructura")
        return self._build_result(vulnerabilities)

    def _analyze_dockerfile(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        base_image = ""
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            if line_stripped.upper().startswith("FROM "):
                base_image = line_stripped.replace("FROM ", "").strip()
                if "latest" in base_image:
                    findings.append({
                        "tipo": "Docker - Latest Tag",
                        "nombre": "Uso de tag 'latest' en imagen base",
                        "descripcion": f"La imagen base {base_image} usa el tag 'latest' que no es reproducible",
                        "severidad": "media",
                        "cvss_score": 4.0,
                        "linea_inicio": i, "linea_fin": i,
                        "codigo_vulnerable": line_stripped,
                        "codigo_corregido": f"FROM {base_image.replace(':latest', ':')}sha256-pinned",
                        "recomendacion": "Usar un tag de versión específico o SHA256 pinning en lugar de 'latest'",
                        "fuente": "Trivy", "archivo_ruta": filepath,
                    })
                if "alpine" not in base_image.lower() and "slim" not in base_image.lower() and "scratch" not in base_image.lower() and "distroless" not in base_image.lower():
                    findings.append({
                        "tipo": "Docker - Image Size",
                        "nombre": "Imagen base no optimizada",
                        "descripcion": "Usar imágenes slim/alpine/distroless reduce superficie de ataque",
                        "severidad": "baja",
                        "cvss_score": 2.1,
                        "linea_inicio": i, "linea_fin": i,
                        "codigo_vulnerable": line_stripped,
                        "codigo_corregido": line_stripped.replace(base_image.split(":")[0], f"{base_image.split(':')[0]}:slim"),
                        "recomendacion": "Usar imágenes slim, alpine o distroless para reducir superficie de ataque",
                        "fuente": "Trivy", "archivo_ruta": filepath,
                    })

            if "USER root" in line_stripped or (line_stripped.upper().startswith("USER") and "root" in line_stripped.lower()):
                findings.append({
                    "tipo": "Docker - Root User",
                    "nombre": "Contenedor ejecutándose como root",
                    "descripcion": "Ejecutar como root dentro del contenedor es una mala práctica de seguridad",
                    "severidad": "alta",
                    "cvss_score": 7.0,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line_stripped,
                    "codigo_corregido": "RUN addgroup -S appgroup && adduser -S appuser -G appgroup\nUSER appuser",
                    "recomendacion": "Crear y usar un usuario no root dentro del contenedor",
                    "fuente": "Trivy", "archivo_ruta": filepath,
                })

            if "RUN" in line_stripped and any(kw in line_stripped.upper() for kw in ["APT-GET", "APK", "YUM", "DNF"]) and "install" in line_stripped.lower():
                if "-y" not in line_stripped and "--yes" not in line_stripped and "-q" not in line_stripped:
                    findings.append({
                        "tipo": "Docker - Non-interactive",
                        "nombre": "Instalación no interactiva sin flag -y",
                        "descripcion": "El comando apt-get/apk puede quedar en espera de confirmación",
                        "severidad": "baja",
                        "cvss_score": 2.0,
                        "linea_inicio": i, "linea_fin": i,
                        "codigo_vulnerable": line_stripped,
                        "codigo_corregido": line_stripped.replace("apt-get", "apt-get -y") if "apt-get" in line_stripped else line_stripped,
                        "recomendacion": "Agregar -y o --yes para instalaciones no interactivas",
                        "fuente": "Trivy", "archivo_ruta": filepath,
                    })

            if "EXPOSE " in line_stripped:
                port = line_stripped.replace("EXPOSE", "").strip()
                try:
                    port_num = int(port.split("/")[0].strip())
                    if port_num in (22, 23, 3389):
                        findings.append({
                            "tipo": "Docker - Insecure Port",
                            "nombre": f"Puerto inseguro expuesto: {port_num}",
                            "descripcion": "Puertos de administración remota expuestos en el contenedor",
                            "severidad": "alta",
                            "cvss_score": 7.5,
                            "linea_inicio": i, "linea_fin": i,
                            "codigo_vulnerable": line_stripped,
                            "codigo_corregido": f"# Eliminar exposición de puerto {port_num} a menos que sea estrictamente necesario",
                            "recomendacion": "No exponer puertos de administración (SSH, Telnet, RDP) en contenedores",
                            "fuente": "Trivy", "archivo_ruta": filepath,
                        })
                except ValueError:
                    pass

        if not any("USER" in l and l.strip().upper().startswith("USER") and "root" not in l.lower() for l in lines):
            if not any("USER" in l and l.strip().upper().startswith("USER") for l in lines):
                findings.append({
                    "tipo": "Docker - Missing USER",
                    "nombre": "Falta instrucción USER - por defecto root",
                    "descripcion": "Sin instrucción USER explícita, el contenedor ejecuta como root",
                    "severidad": "alta",
                    "cvss_score": 7.0,
                    "linea_inicio": len(lines),
                    "linea_fin": len(lines),
                    "codigo_vulnerable": "# No hay USER instruction",
                    "codigo_corregido": "RUN addgroup -S appgroup && adduser -S appuser -G appgroup\nUSER appuser",
                    "recomendacion": "Agregar instrucción USER al final del Dockerfile con usuario no root",
                    "fuente": "Trivy", "archivo_ruta": filepath,
                })

        if not any("COPY --chown" in l and "appuser" in l for l in lines):
            if any("COPY" in l and l.strip().upper().startswith("COPY") for l in lines):
                pass

        return findings

    def _analyze_compose(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "ports:" in line or "- '" in line and ":" in line and not "version" in line:
                port_match = re.search(r'"(\d+):', line) or re.search(r"'(\d+)'", line)
                if port_match:
                    port = int(port_match.group(1))
                    if port == 3306 or port == 5432:
                        findings.append({
                            "tipo": "Docker - Database Port Exposed",
                            "nombre": f"Puerto de base de datos expuesto: {port}",
                            "descripcion": "Base de datos expuesta al host, posible fuga de datos si no hay autenticación fuerte",
                            "severidad": "media",
                            "cvss_score": 5.0,
                            "linea_inicio": i, "linea_fin": i,
                            "codigo_vulnerable": line.strip(),
                            "codigo_corregido": "Usar red interna de docker (no publicar puerto) o limitar bind a 127.0.0.1:puerto",
                            "recomendacion": "Las bases de datos no deberían exponerse fuera de la red Docker",
                            "fuente": "Trivy", "archivo_ruta": filepath,
                        })

        return findings

    def _analyze_kubernetes(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "privileged: true" in line:
                findings.append({
                    "tipo": "K8s - Privileged Container",
                    "nombre": "Contenedor privilegiado en Kubernetes",
                    "descripcion": "Ejecutar contenedores privilegiados rompe el aislamiento de seguridad",
                    "severidad": "crítica",
                    "cvss_score": 9.0,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "privileged: false",
                    "recomendacion": "Establecer securityContext con privileged: false. Solo usar si es absolutamente necesario",
                    "fuente": "Trivy", "archivo_ruta": filepath,
                })

            if "runAsUser: 0" in line or "runAsRoot: true" in line:
                findings.append({
                    "tipo": "K8s - Container as Root",
                    "nombre": "Contenedor ejecutándose como root en K8s",
                    "descripcion": "Ejecutar como root en Kubernetes es una violación de seguridad",
                    "severidad": "alta",
                    "cvss_score": 7.5,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "runAsUser: 1000\nrunAsNonRoot: true",
                    "recomendacion": "Configurar securityContext.runAsNonRoot: true y runAsUser > 1000",
                    "fuente": "Trivy", "archivo_ruta": filepath,
                })

        return findings
