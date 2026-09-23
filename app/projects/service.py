import os
import zipfile
import hashlib
import shutil
import tempfile
from typing import Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.projects.models import Proyecto, ArchivoProyecto, Lenguaje, Framework, EstadoProyecto
from app.projects.detector import LanguageDetector
from app.projects.parser import DependencyParser
from app.exceptions import NotFoundException, ValidationException
import logging

logger = logging.getLogger("securecode.projects")


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.detector = LanguageDetector()
        self.parser = DependencyParser()

    async def create_project(self, nombre: str, user_id: int, descripcion: Optional[str] = None,
                             repo_url: Optional[str] = None, repo_tipo: Optional[str] = "zip") -> Proyecto:
        project = Proyecto(
            nombre=nombre,
            descripcion=descripcion,
            repo_url=repo_url,
            repo_tipo=repo_tipo,
            user_id=user_id,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: int) -> Proyecto:
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(Proyecto).options(selectinload(Proyecto.auditorias)).where(Proyecto.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise NotFoundException("Proyecto no encontrado")
        return project

    async def get_user_projects(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Proyecto]:
        result = await self.db.execute(
            select(Proyecto).where(Proyecto.user_id == user_id)
            .offset(skip).limit(limit).order_by(Proyecto.created_at.desc())
        )
        return result.scalars().all()

    async def get_all_projects(self, skip: int = 0, limit: int = 100) -> list[Proyecto]:
        result = await self.db.execute(
            select(Proyecto).offset(skip).limit(limit).order_by(Proyecto.created_at.desc())
        )
        return result.scalars().all()

    async def get_projects_with_counts(self, skip: int = 0, limit: int = 100) -> list[tuple]:
        """Lista proyectos con conteos agregados en 3 queries (evita cargar contenido)."""
        projects = (
            await self.db.execute(
                select(Proyecto).order_by(Proyecto.created_at.desc()).offset(skip).limit(limit)
            )
        ).scalars().all()
        if not projects:
            return []
        projects, file_counts, audit_counts = await self._attach_counts(projects)
        return [
            (p, file_counts.get(p.id, 0), audit_counts.get(p.id, 0)) for p in projects
        ]

    async def get_user_projects_with_counts(self, user_id: int, skip: int = 0, limit: int = 100) -> tuple:
        """Lista proyectos del usuario con conteos agregados en 3 queries.
        Devuelve (projects, file_counts, audit_counts)."""
        projects = (
            await self.db.execute(
                select(Proyecto)
                .where(Proyecto.user_id == user_id)
                .order_by(Proyecto.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()
        if not projects:
            return [], {}, {}
        return await self._attach_counts(projects)

    async def _attach_counts(self, projects: list[Proyecto]) -> tuple:
        from app.audits.models import Auditoria
        ids = [p.id for p in projects]
        file_counts = dict(
            (
                await self.db.execute(
                    select(ArchivoProyecto.proyecto_id, func.count())
                    .where(ArchivoProyecto.proyecto_id.in_(ids))
                    .group_by(ArchivoProyecto.proyecto_id)
                )
            ).all()
        )
        audit_counts = dict(
            (
                await self.db.execute(
                    select(Auditoria.proyecto_id, func.count())
                    .where(Auditoria.proyecto_id.in_(ids))
                    .group_by(Auditoria.proyecto_id)
                )
            ).all()
        )
        return projects, file_counts, audit_counts

    async def count_project_files(self, project_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ArchivoProyecto).where(
                ArchivoProyecto.proyecto_id == project_id
            )
        )
        return result.scalar() or 0

    async def count_project_auditorias(self, project_id: int) -> int:
        from app.audits.models import Auditoria
        result = await self.db.execute(
            select(func.count()).select_from(Auditoria).where(
                Auditoria.proyecto_id == project_id
            )
        )
        return result.scalar() or 0

    async def list_files_meta(self, project_id: int) -> list[ArchivoProyecto]:
        """Solo metadatos de archivos (sin contenido) para listados ligeros."""
        result = await self.db.execute(
            select(
                ArchivoProyecto.id,
                ArchivoProyecto.proyecto_id,
                ArchivoProyecto.ruta,
                ArchivoProyecto.hash,
                ArchivoProyecto.tamano,
                ArchivoProyecto.lenguaje,
            ).where(ArchivoProyecto.proyecto_id == project_id)
        )
        return result.all()

    async def update_project(self, project_id: int, data: dict) -> Proyecto:
        project = await self.get_project(project_id)
        for key, value in data.items():
            if value is not None and hasattr(project, key):
                setattr(project, key, value)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int):
        project = await self.get_project(project_id)
        await self.db.delete(project)
        await self.db.commit()

    async def process_upload(self, project_id: int, file_path: str, project_dir: str) -> dict:
        import posixpath
        project = await self.get_project(project_id)

        # --- Límites de seguridad para evitar ZIP bombs y uploads inmanejables ---
        MAX_MEMBERS = 20000          # máximo de archivos dentro del zip
        MAX_TOTAL_UNCOMPRESSED_MB = 2048  # 2 GB descomprimidos en total
        MAX_RAW_FILE_MB = 20         # archivos individuales mayores se ignoran
        # Carpetas que se ignoran siempre (node_modules, git, venv, builds...)
        SKIP_DIRS = {
            "node_modules", ".git", "__pycache__", "venv", ".venv",
            "dist", "build", ".next", ".nuxt", ".idea", ".vscode",
            "target", ".terraform", "vendor", "site-packages",
        }
        MAX_CONTENT_BYTES = 65000    # límite de la columna TEXT de MySQL

        # Limpieza de subidas anteriores (idempotencia).
        # Se borran primero las auditorías del proyecto (sus vulnerabilidades
        # referencian archivos por FK), luego los archivos.
        from app.audits.models import Auditoria as AudMod
        existing_audits = (
            await self.db.execute(
                select(AudMod).where(AudMod.proyecto_id == project_id)
            )
        ).scalars().all()
        for a in existing_audits:
            await self.db.delete(a)  # cascade: resultados, vulnerabilidades, tareas, mapeos
        await self.db.flush()
        await self.db.execute(
            text("DELETE FROM sc_archivos_proyecto WHERE proyecto_id = :pid"),
            {"pid": project_id},
        )

        def is_binary(raw: bytes) -> bool:
            return b"\x00" in raw[:8192]

        def path_is_safe(member_name: str) -> bool:
            if member_name.startswith(("/", "\\")):
                return False
            if "\\" in member_name and member_name.split("\\")[0].endswith(":"):
                return False  # ruta Windows tipo C:\\
            parts = posixpath.normpath(member_name.replace("\\", "/")).split("/")
            if ".." in parts:
                return False  # zip-slip
            return True

        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                infos = [i for i in zip_ref.infolist() if not i.is_dir()]
                if len(infos) > MAX_MEMBERS:
                    raise ValidationException(
                        f"El ZIP contiene {len(infos)} archivos (máximo {MAX_MEMBERS}). "
                        "Posiblemente incluye node_modules u otras carpetas generadas."
                    )
                total_uncompressed = sum(i.file_size for i in infos)
                if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_MB * 1024 * 1024:
                    raise ValidationException(
                        f"El ZIP descomprimido pesa ~{total_uncompressed // (1024*1024)} MB "
                        f"(máximo {MAX_TOTAL_UNCOMPRESSED_MB} MB)."
                    )

                files = []
                for info in infos:
                    name = info.filename
                    if not path_is_safe(name):
                        raise ValidationException(
                            f"El ZIP contiene rutas inseguras ({name!r}). Rechazado por seguridad."
                        )
                    if info.flag_bits & 0x1:
                        raise ValidationException("El ZIP contiene archivos cifrados; no se soporta.")
                    if info.file_size > MAX_RAW_FILE_MB * 1024 * 1024:
                        continue  # archivo demasiado grande -> se omite
                    parts = posixpath.normpath(name.replace("\\", "/")).split("/")
                    if any(p in SKIP_DIRS for p in parts[:-1]):
                        continue  # dentro de carpeta ignorada
                    try:
                        raw = zip_ref.read(info)
                    except Exception as exc:
                        logger.warning(f"Archivo no leíble en ZIP ({name}): {exc}")
                        continue
                    rel_path = name.replace("\\", "/")
                    if is_binary(raw):
                        continue  # binarios/imágenes no se analizan
                    # Truncar a bytes antes de guardar (igual que la vía git)
                    contenido = raw.decode("utf-8", errors="replace").encode("utf-8")[:MAX_CONTENT_BYTES].decode("utf-8", errors="replace")
                    file_hash = hashlib.sha256(raw).hexdigest()
                    lenguaje = self.detector.detect_language(rel_path)
                    archivo = ArchivoProyecto(
                        proyecto_id=project_id,
                        ruta=rel_path,
                        hash=file_hash,
                        tamano=len(raw),
                        lenguaje=lenguaje,
                        contenido=contenido,
                    )
                    self.db.add(archivo)
                    files.append(archivo)

                project.lenguaje = self.detector.detect_project_language(files)
                project.framework = self.detector.detect_framework_from_files(files)
                project.estado = EstadoProyecto.EN_REVISION.value
                await self.db.commit()

                return {
                    "total_files": len(files),
                    "ignored": len(infos) - len(files),
                    "lenguaje": project.lenguaje,
                    "framework": project.framework,
                }

        except zipfile.BadZipFile:
            await self.db.rollback()
            raise ValidationException("El archivo subido no es un ZIP válido.")
        except zipfile.LargeZipFile:
            await self.db.rollback()
            raise ValidationException("El ZIP usa funciones no soportadas (too large).")
        except ValidationException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error procesando ZIP del proyecto {project_id}")
            raise ValidationException(f"Error procesando el ZIP: {e}")

    async def get_project_auditorias(self, project_id: int) -> list:
        from app.audits.models import Auditoria
        result = await self.db.execute(
            select(Auditoria).where(Auditoria.proyecto_id == project_id)
        )
        return result.scalars().all()

    async def get_project_files(self, project_id: int) -> list[ArchivoProyecto]:
        result = await self.db.execute(
            select(ArchivoProyecto).where(ArchivoProyecto.proyecto_id == project_id)
        )
        return result.scalars().all()

    async def get_project_stats(self, project_id: int) -> dict:
        project = await self.get_project(project_id)
        result = await self.db.execute(
            select(func.count()).select_from(ArchivoProyecto).where(
                ArchivoProyecto.proyecto_id == project_id
            )
        )
        total_files = result.scalar()

        auditorias = await self.get_project_auditorias(project_id)
        return {
            "total_files": total_files,
            "lenguaje": project.lenguaje,
            "framework": project.framework,
            "total_audits": len(auditorias),
            "latest_audit_status": auditorias[-1].estado if auditorias else None,
        }
