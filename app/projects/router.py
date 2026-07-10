import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.projects.service import ProjectService
from app.projects.schemas import ProyectoCreate, ProyectoUpdate, ProyectoResponse, ArchivoResponse
from app.dependencies import get_current_active_user, require_role
from app.auth.models import Usuario
from app.config import settings

router = APIRouter()


@router.get("/", response_model=List[ProyectoResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    projects = await service.get_all_projects(skip, limit)

    result = []
    for p in projects:
        files = await service.get_project_files(p.id)
        auditorias = await service.get_project_auditorias(p.id)
        resp = ProyectoResponse(
            id=p.id,
            nombre=p.nombre,
            descripcion=p.descripcion,
            lenguaje=p.lenguaje,
            framework=p.framework,
            repo_url=p.repo_url,
            repo_tipo=p.repo_tipo,
            estado=p.estado,
            version_actual=p.version_actual,
            user_id=p.user_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
            archivos_count=len(files),
            auditorias_count=len(auditorias),
        )
        result.append(resp)
    return result


@router.post("/", response_model=ProyectoResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProyectoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    project = await service.create_project(
        nombre=data.nombre,
        descripcion=data.descripcion,
        user_id=current_user.id,
        repo_url=data.repo_url,
        repo_tipo=data.repo_tipo,
    )
    return ProyectoResponse(
        id=project.id,
        nombre=project.nombre,
        descripcion=project.descripcion,
        lenguaje=project.lenguaje,
        framework=project.framework,
        repo_url=project.repo_url,
        repo_tipo=project.repo_tipo,
        estado=project.estado,
        version_actual=project.version_actual,
        user_id=project.user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archivos_count=0,
        auditorias_count=0,
    )


@router.get("/{project_id}", response_model=ProyectoResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    project = await service.get_project(project_id)
    files = await service.get_project_files(project_id)
    auditorias = await service.get_project_auditorias(project_id)
    return ProyectoResponse(
        id=project.id,
        nombre=project.nombre,
        descripcion=project.descripcion,
        lenguaje=project.lenguaje,
        framework=project.framework,
        repo_url=project.repo_url,
        repo_tipo=project.repo_tipo,
        estado=project.estado,
        version_actual=project.version_actual,
        user_id=project.user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archivos_count=len(files),
        auditorias_count=len(auditorias),
    )


@router.put("/{project_id}", response_model=ProyectoResponse)
async def update_project(
    project_id: int,
    data: ProyectoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    project = await service.update_project(project_id, data.model_dump(exclude_none=True))
    files = await service.get_project_files(project_id)
    auditorias = await service.get_project_auditorias(project_id)
    return ProyectoResponse(
        id=project.id,
        nombre=project.nombre,
        descripcion=project.descripcion,
        lenguaje=project.lenguaje,
        framework=project.framework,
        repo_url=project.repo_url,
        repo_tipo=project.repo_tipo,
        estado=project.estado,
        version_actual=project.version_actual,
        user_id=project.user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        archivos_count=len(files),
        auditorias_count=len(auditorias),
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    await service.delete_project(project_id)


@router.post("/{project_id}/upload")
async def upload_project_files(
    project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    project_dir = os.path.join(settings.APP_STORAGE_DIR, f"project_{project_id}")
    os.makedirs(project_dir, exist_ok=True)
    zip_path = os.path.join(project_dir, file.filename or "upload.zip")

    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)

    service = ProjectService(db)
    result = await service.process_upload(project_id, zip_path, project_dir)
    return {"message": "Archivos procesados correctamente", **result}


@router.get("/{project_id}/files", response_model=List[ArchivoResponse])
async def get_project_files(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    return await service.get_project_files(project_id)


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    return await service.get_project_stats(project_id)
