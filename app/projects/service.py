import os
import zipfile
import hashlib
import shutil
import tempfile
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.projects.models import Proyecto, ArchivoProyecto, Lenguaje, Framework, EstadoProyecto
from app.projects.detector import LanguageDetector
from app.projects.parser import DependencyParser
from app.exceptions import NotFoundException, ValidationException


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
        project = await self.get_project(project_id)
        extract_dir = os.path.join(project_dir, "src")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        files = []
        for root, dirs, filenames in os.walk(extract_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, extract_dir)
                file_size = os.path.getsize(full_path)

                with open(full_path, 'rb') as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()

                lenguaje = self.detector.detect_language(rel_path)

                archivo = ArchivoProyecto(
                    proyecto_id=project_id,
                    ruta=rel_path.replace("\\", "/"),
                    hash=file_hash,
                    tamano=file_size,
                    lenguaje=lenguaje,
                )
                self.db.add(archivo)
                files.append(archivo)

        project.lenguaje = self.detector.detect_project_language(files)
        project.framework = self.detector.detect_framework(extract_dir)
        project.estado = EstadoProyecto.EN_REVISION.value
        await self.db.commit()

        return {
            "total_files": len(files),
            "lenguaje": project.lenguaje,
            "framework": project.framework,
        }

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
        files = await self.get_project_files(project_id)

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
