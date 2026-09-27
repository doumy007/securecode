import os
import zipfile
import hashlib
import shutil
import tempfile
from typing import Optional
from sqlalchemy import select, func, text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from app.projects.models import Proyecto, ArchivoProyecto, Lenguaje, Framework, EstadoProyecto
from app.projects.detector import LanguageDetector
from app.projects.parser import DependencyParser
from app.exceptions import NotFoundException, ValidationException
import logging

logger = logging.getLogger("securecode.projects")


def sql_quote(value) -> str:
    """Escapa un valor para un literal SQL (INSERTs masivos multi-VALUES)."""
    if value is None:
        return "NULL"
    s = str(value)
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def chunk_for_insert(files, max_rows=100, max_bytes=4 * 1024 * 1024):
    """Divide archivos en lotes acotados por filas y por tamaño estimado para
    no superar max_allowed_packet de MySQL en un solo INSERT multi-VALUES."""
    current, total = [], 0
    for f in files:
        est = (len(f.contenido) if f.contenido else 0) + 256
        if current and (len(current) >= max_rows or total + est > max_bytes):
            yield current
            current, total = [], 0
        current.append(f)
        total += est
    if current:
        yield current


async def bulk_insert_files(db, files, proyecto_id, auditoria_id=None):
    """INSERT en lote (multi-VALUES) para archivos de proyecto/snapshot.

    La BD remota es lenta por latencia: un INSERT por fila vía ORM tardaba
    ~0,23 s/archivo (400 archivos -> 90 s, superaba el timeout del frontend),
    mientras que un INSERT multi-VALUES por lote termina en 1-3 s."""
    INSERT_SQL = (
        "INSERT INTO sc_archivos_proyecto "
        "(proyecto_id, auditoria_id, ruta, hash, tamano, lenguaje, contenido) VALUES "
    )
    aid_sql = "NULL" if auditoria_id is None else str(int(auditoria_id))
    for chunk in chunk_for_insert(files):
        values = ",".join(
            f"({proyecto_id}, {aid_sql}, {sql_quote(f.ruta)}, {sql_quote(f.hash)}, "
            f"{f.tamano if f.tamano is not None else 'NULL'}, {sql_quote(f.lenguaje)}, "
            f"{sql_quote(f.contenido)})"
            for f in chunk
        )
        await db.execute(text(INSERT_SQL + values))


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
        # "Archivos" del proyecto = código actual: el snapshot más reciente
        # (reclamado por una auditoría) o, si no hay, el lote pendiente (NULL).
        file_counts = dict(
            (
                await self.db.execute(
                    text(
                        """
                        SELECT f.proyecto_id, COUNT(*) FROM sc_archivos_proyecto f
                        WHERE f.proyecto_id IN :ids
                          AND (
                            f.auditoria_id = (
                              SELECT f2.auditoria_id FROM sc_archivos_proyecto f2
                              WHERE f2.proyecto_id = f.proyecto_id
                                AND f2.auditoria_id IS NOT NULL
                              ORDER BY f2.id DESC LIMIT 1
                            )
                            OR (
                              f.auditoria_id IS NULL
                              AND NOT EXISTS (
                                SELECT 1 FROM sc_archivos_proyecto f3
                                WHERE f3.proyecto_id = f.proyecto_id
                                  AND f3.auditoria_id IS NOT NULL
                              )
                            )
                          )
                        GROUP BY f.proyecto_id
                        """
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": ids},
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

    async def _current_snapshot_auditoria_id(self, project_id: int) -> Optional[int]:
        """auditoria_id del snapshot más reciente del proyecto, o None."""
        return (
            await self.db.execute(
                select(ArchivoProyecto.auditoria_id)
                .where(
                    ArchivoProyecto.proyecto_id == project_id,
                    ArchivoProyecto.auditoria_id.isnot(None),
                )
                .order_by(ArchivoProyecto.id.desc())
                .limit(1)
            )
        ).scalar()

    async def count_project_files(self, project_id: int) -> int:
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM sc_archivos_proyecto f
                WHERE f.proyecto_id = :pid
                  AND (
                    f.auditoria_id = (
                      SELECT f2.auditoria_id FROM sc_archivos_proyecto f2
                      WHERE f2.proyecto_id = :pid AND f2.auditoria_id IS NOT NULL
                      ORDER BY f2.id DESC LIMIT 1
                    )
                    OR (
                      f.auditoria_id IS NULL
                      AND NOT EXISTS (
                        SELECT 1 FROM sc_archivos_proyecto f3
                        WHERE f3.proyecto_id = :pid AND f3.auditoria_id IS NOT NULL
                      )
                    )
                  )
                """
            ),
            {"pid": project_id},
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
        """Metadatos (sin contenido) del código actual del proyecto:
        el snapshot más reciente, o el lote pendiente si no hay auditoría aún."""
        latest_aid = await self._current_snapshot_auditoria_id(project_id)
        conditions = [ArchivoProyecto.proyecto_id == project_id]
        if latest_aid is not None:
            conditions.append(ArchivoProyecto.auditoria_id == latest_aid)
        else:
            conditions.append(ArchivoProyecto.auditoria_id.is_(None))
        result = await self.db.execute(
            select(
                ArchivoProyecto.id,
                ArchivoProyecto.proyecto_id,
                ArchivoProyecto.ruta,
                ArchivoProyecto.hash,
                ArchivoProyecto.tamano,
                ArchivoProyecto.lenguaje,
            ).where(*conditions)
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
        # Verificar existencia (404), igual que el comportamiento anterior.
        exists = (
            await self.db.execute(
                text("SELECT 1 FROM sc_proyectos WHERE id = :pid"), {"pid": project_id}
            )
        ).scalar()
        if not exists:
            raise NotFoundException("Proyecto no encontrado")

        # Borrado masivo por SQL en orden de dependencias (FK). El borrado ORM
        # emitía un DELETE por fila a través de la BD remota y tardaba 17-44 s,
        # superando el timeout de 30 s del frontend ("La petición tardó
        # demasiado"). Con DELETE en lote por tabla se hace en 1-3 s.
        audit_ids = (
            await self.db.execute(
                text("SELECT id FROM sc_auditorias WHERE proyecto_id = :pid"),
                {"pid": project_id},
            )
        ).scalars().all()
        if audit_ids:
            params = {"aids": audit_ids}
            aids = bindparam("aids", expanding=True)
            await self.db.execute(
                text("DELETE FROM sc_historial_ejecuciones WHERE auditoria_id IN :aids").bindparams(aids),
                params,
            )
            await self.db.execute(
                text(
                    "DELETE FROM sc_mapeo_estandares "
                    "WHERE vulnerabilidad_id IN ("
                    "SELECT id FROM sc_vulnerabilidades WHERE auditoria_id IN :aids)"
                ).bindparams(aids),
                params,
            )
            await self.db.execute(
                text("DELETE FROM sc_tareas_remediacion WHERE auditoria_id IN :aids").bindparams(aids),
                params,
            )
            await self.db.execute(
                text("DELETE FROM sc_resultados_worker WHERE auditoria_id IN :aids").bindparams(aids),
                params,
            )
            await self.db.execute(
                text("DELETE FROM sc_vulnerabilidades WHERE auditoria_id IN :aids").bindparams(aids),
                params,
            )
            await self.db.execute(
                text("DELETE FROM sc_auditorias WHERE id IN :aids").bindparams(aids),
                params,
            )
        await self.db.execute(
            text("DELETE FROM sc_archivos_proyecto WHERE proyecto_id = :pid"),
            {"pid": project_id},
        )
        await self.db.execute(
            text("DELETE FROM sc_proyectos WHERE id = :pid"),
            {"pid": project_id},
        )
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

        # Los archivos subidos por ZIP quedan como snapshot "pendiente" (auditoria_id
        # NULL) que la próxima auditoría sin origen git reclamará al crearse.
        # NO se borran las auditorías existentes ni sus archivos: cada auditoría
        # conserva su propio código y análisis por separado.
        # Solo se limpian pendientes huérfanos SIN referencia desde alguna
        # vulnerabilidad (los que quedaron de una subida nunca auditada).
        await self.db.execute(
            text(
                "DELETE FROM sc_archivos_proyecto "
                "WHERE proyecto_id = :pid AND auditoria_id IS NULL "
                "AND id NOT IN (SELECT archivo_id FROM sc_vulnerabilidades WHERE archivo_id IS NOT NULL)"
            ),
            {"pid": project_id},
        )
        await self.db.flush()

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
                    files.append(archivo)

                # INSERT por lotes multi-VALUES (la vía ORM tarda 0,23 s/archivo
                # contra la BD remota y un ZIP grande superaba el timeout del
                # frontend).
                await bulk_insert_files(self.db, files, project_id)

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

    async def get_audit_source_files(self, project_id: int, audit_id: int) -> list[ArchivoProyecto]:
        """Código que debe analizar una auditoría SIN origen git:
        1) su propio snapshot (reclamado al crearse); 2) si no, el lote
        pendiente (ZIP subido aún sin auditoría) -> se reclama para esta
        auditoría; 3) si no, el snapshot más reciente del proyecto."""
        rows = (
            await self.db.execute(
                select(ArchivoProyecto).where(
                    ArchivoProyecto.proyecto_id == project_id,
                    ArchivoProyecto.auditoria_id == audit_id,
                )
            )
        ).scalars().all()
        if rows:
            return rows

        from app.audits.models import Vulnerabilidad
        rows = (
            await self.db.execute(
                select(ArchivoProyecto).where(
                    ArchivoProyecto.proyecto_id == project_id,
                    ArchivoProyecto.auditoria_id.is_(None),
                    ArchivoProyecto.id.not_in(
                        select(Vulnerabilidad.archivo_id).where(
                            Vulnerabilidad.archivo_id.isnot(None)
                        )
                    ),
                )
            )
        ).scalars().all()
        if rows:
            ids = [r.id for r in rows]
            await self.db.execute(
                text("UPDATE sc_archivos_proyecto SET auditoria_id = :aid WHERE id IN :ids")
                .bindparams(bindparam("ids", expanding=True)),
                {"aid": audit_id, "ids": ids},
            )
            await self.db.commit()
            return rows

        latest_aid = await self._current_snapshot_auditoria_id(project_id)
        if latest_aid is None:
            return []
        return (
            await self.db.execute(
                select(ArchivoProyecto).where(ArchivoProyecto.auditoria_id == latest_aid)
            )
        ).scalars().all()

    async def get_project_stats(self, project_id: int) -> dict:
        project = await self.get_project(project_id)
        total_files = await self.count_project_files(project_id)

        auditorias = await self.get_project_auditorias(project_id)
        return {
            "total_files": total_files,
            "lenguaje": project.lenguaje,
            "framework": project.framework,
            "total_audits": len(auditorias),
            "latest_audit_status": auditorias[-1].estado if auditorias else None,
        }

    async def get_project_audits_with_counts(self, project_id: int) -> list[dict]:
        """Auditorías del proyecto con su número de vulnerabilidades, en una
        sola agregación SQL (1 round-trip a la BD remota, que es lenta)."""
        from app.audits.models import Auditoria, Vulnerabilidad

        rows = (
            await self.db.execute(
                select(Auditoria, func.count(Vulnerabilidad.id).label("cnt"))
                .outerjoin(Vulnerabilidad, Vulnerabilidad.auditoria_id == Auditoria.id)
                .where(Auditoria.proyecto_id == project_id)
                .group_by(Auditoria.id)
                .order_by(Auditoria.created_at.desc())
            )
        ).all()
        return [
            {
                "id": a.id,
                "nombre": a.nombre or f"Auditoría #{a.id}",
                "estado": a.estado,
                "tipo": a.tipo,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                "vulnerabilities_count": int(cnt or 0),
            }
            for a, cnt in rows
        ]
