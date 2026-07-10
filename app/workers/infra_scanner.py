from app.workers.base import BaseWorker
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto
import logging
import re

logger = logging.getLogger("securecode.workers")


class InfraScannerWorker(BaseWorker):
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        logger.info(f"InfraScannerWorker: Escaneando archivos IaC del proyecto {project.id}")
        vulnerabilities = []

        for f in files:
            if not f.contenido:
                continue

            if f.ruta.endswith(".tf") or f.ruta.endswith(".tfvars"):
                findings = self._scan_terraform(f.ruta, f.contenido)
                vulnerabilities.extend(findings)

            if f.ruta.endswith("Chart.yaml") or f.ruta.endswith("values.yaml") or "helm" in f.ruta.lower():
                findings = self._scan_helm(f.ruta, f.contenido)
                vulnerabilities.extend(findings)

            if f.ruta.endswith(".env") or f.ruta.endswith(".env.example"):
                findings = self._scan_env_file(f.ruta, f.contenido)
                vulnerabilities.extend(findings)

            if ".gitignore" in f.ruta:
                findings = self._scan_gitignore(f.ruta, f.contenido)
                vulnerabilities.extend(findings)

            if f.ruta.endswith(".pem") or f.ruta.endswith(".key") or f.ruta.endswith("id_rsa"):
                vulnerabilities.append({
                    "tipo": "IaC - Private Key",
                    "nombre": "Clave privada incluida en el repositorio",
                    "descripcion": f"Archivo de clave privada encontrado: {f.ruta}",
                    "severidad": "crítica",
                    "cvss_score": 9.5,
                    "linea_inicio": 0, "linea_fin": 0,
                    "codigo_vulnerable": f"Archivo: {f.ruta}",
                    "codigo_corregido": "Eliminar del repositorio. Agregar a .gitignore.",
                    "recomendacion": "Nunca incluir claves privadas en el repositorio. Usar vault/secret manager",
                    "fuente": "InfraScanner", "archivo_ruta": f.ruta,
                })

        logger.info(f"InfraScannerWorker: {len(vulnerabilities)} hallazgos")
        return self._build_result(vulnerabilities)

    def _scan_terraform(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "aws_iam_access_key" in line or "aws_secret_key" in line:
                findings.append({
                    "tipo": "Terraform - Hardcoded AWS Key",
                    "nombre": "Clave AWS hardcodeada en Terraform",
                    "descripcion": "Las claves AWS no deben estar en archivos .tf",
                    "severidad": "crítica", "cvss_score": 9.5,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": 'variable "aws_access_key" {}\nUsar: var.aws_access_key',
                    "recomendacion": "Usar variables de entorno AWS_ACCESS_KEY_ID en lugar de hardcodear",
                    "fuente": "InfraScanner", "archivo_ruta": filepath,
                })

            if 'ingress' in line.lower() and '0.0.0.0/0' in line:
                findings.append({
                    "tipo": "Terraform - Open Ingress",
                    "nombre": "Security Group abierto a 0.0.0.0/0",
                    "descripcion": "El security group permite acceso desde cualquier IP",
                    "severidad": "alta", "cvss_score": 7.5,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": 'cidr_blocks = ["10.0.0.0/8"]  # Restringir a IPs necesarias',
                    "recomendacion": "Restringir ingress a rangos IP específicos necesarios",
                    "fuente": "InfraScanner", "archivo_ruta": filepath,
                })

            if "s3_bucket" in line.lower() and "acl" in line.lower() and "public" in line.lower():
                findings.append({
                    "tipo": "Terraform - Public S3 Bucket",
                    "nombre": "Bucket S3 con acceso público",
                    "descripcion": "Bucket S3 configurado como público",
                    "severidad": "alta", "cvss_score": 7.8,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": 'acl = "private"  # o usar block_public_acls = true',
                    "recomendacion": "Configurar buckets S3 como privados y bloquear acceso público",
                    "fuente": "InfraScanner", "archivo_ruta": filepath,
                })

        return findings

    def _scan_helm(self, filepath: str, content: str) -> list:
        findings = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "replicaCount" in line and "1" in line and "replicaCount" in line.split(":")[0]:
                pass

            if "serviceAccount" in line and "create: false" in line:
                findings.append({
                    "tipo": "Helm - No ServiceAccount",
                    "nombre": "ServiceAccount no creado para el pod",
                    "descripcion": "Sin service account dedicada, el pod usa la default",
                    "severidad": "media", "cvss_score": 4.5,
                    "linea_inicio": i, "linea_fin": i,
                    "codigo_vulnerable": line.strip(),
                    "codigo_corregido": "serviceAccount:\n  create: true\n  name: app-sa",
                    "recomendacion": "Crear ServiceAccount dedicada con permisos mínimos",
                    "fuente": "InfraScanner", "archivo_ruta": filepath,
                })

        return findings

    def _scan_env_file(self, filepath: str, content: str) -> list:
        findings = []
        sensitive_keys = ["password", "secret", "key", "token", "credential", "api_key", "apikey"]
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0].strip().lower()
                value = line.split("=")[1].strip().strip('"').strip("'")
                if any(sk in key for sk in sensitive_keys):
                    if value and value != "changeme" and len(value) > 4 and not value.startswith("$"):
                        if not filepath.endswith(".env.example"):
                            findings.append({
                                "tipo": "IaC - Exposed Credential",
                                "nombre": f"Credencial expuesta en archivo .env",
                                "descripcion": f"Variable sensible '{key}' con valor aparentemente real",
                                "severidad": "crítica", "cvss_score": 9.0,
                                "linea_inicio": i, "linea_fin": i,
                                "codigo_vulnerable": line.strip(),
                                "codigo_corregido": f"{key}=${key}  # Usar variable de entorno del sistema",
                                "recomendacion": "Eliminar valores reales de .env del repositorio. Usar secretos en CI/CD",
                                "fuente": "InfraScanner", "archivo_ruta": filepath,
                            })

        return findings

    def _scan_gitignore(self, filepath: str, content: str) -> list:
        findings = []
        required_entries = [".env", "*.pem", "*.key", "secrets", "credentials", "*.log"]
        content_lower = content.lower()
        for entry in required_entries:
            if entry not in content_lower:
                findings.append({
                    "tipo": "IaC - Missing .gitignore",
                    "nombre": f"Falta entrada '{entry}' en .gitignore",
                    "descripcion": f"Archivos {entry} podrían ser commiteados accidentalmente",
                    "severidad": "media", "cvss_score": 5.0,
                    "linea_inicio": 0, "linea_fin": 0,
                    "codigo_vulnerable": f"Falta: {entry}",
                    "codigo_corregido": f"Agregar '{entry}' a .gitignore",
                    "recomendacion": f"Agregar '{entry}' al archivo .gitignore para prevenir fugas accidentales",
                    "fuente": "InfraScanner", "archivo_ruta": filepath,
                })
        return findings
