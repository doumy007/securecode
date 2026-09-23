import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.projects.service import ProjectService
from app.projects.schemas import ProyectoCreate, ProyectoUpdate, ProyectoResponse, ArchivoResponse
from app.dependencies import get_current_active_user, require_role, ensure_project_access
from app.auth.models import Usuario
from app.config import settings
from app.shared.validators import sanitize_filename
from app.exceptions import ValidationException

router = APIRouter()


@router.get("/", response_model=List[ProyectoResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    if current_user.rol.nombre != "admin":
        projects_all, files_counts, audit_counts = await service.get_user_projects_with_counts(
            current_user.id, skip, limit
        )
        result = []
        for p in projects_all:
            result.append(
                _to_response(p, files_counts.get(p.id, 0), audit_counts.get(p.id, 0))
            )
        return result

    result = []
    for p, n_files, n_audits in await service.get_projects_with_counts(skip, limit):
        result.append(_to_response(p, n_files, n_audits))
    return result


def _to_response(p, n_files=0, n_audits=0) -> ProyectoResponse:
    return ProyectoResponse(
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
        archivos_count=n_files,
        auditorias_count=n_audits,
    )


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
    await ensure_project_access(db, project_id, current_user)
    project = await service.get_project(project_id)
    n_files = await service.count_project_files(project_id)
    n_audits = await service.count_project_auditorias(project_id)
    return _to_response(project, n_files, n_audits)


@router.put("/{project_id}", response_model=ProyectoResponse)
async def update_project(
    project_id: int,
    data: ProyectoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    await ensure_project_access(db, project_id, current_user)
    project = await service.update_project(project_id, data.model_dump(exclude_none=True))
    n_files = await service.count_project_files(project_id)
    n_audits = await service.count_project_auditorias(project_id)
    return _to_response(project, n_files, n_audits)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    await ensure_project_access(db, project_id, current_user)
    await service.delete_project(project_id)
    project_dir = os.path.join(settings.APP_STORAGE_DIR, f"project_{project_id}")
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)


@router.post("/{project_id}/upload")
async def upload_project_files(
    project_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    project_dir = os.path.join(settings.APP_STORAGE_DIR, f"project_{project_id}")
    os.makedirs(project_dir, exist_ok=True)

    await ensure_project_access(db, project_id, current_user)

    max_bytes = settings.APP_MAX_UPLOAD_SIZE_MB * 1024 * 1024
    zip_path = os.path.join(project_dir, f"upload_{project_id}.zip")
    try:
        safe_name = sanitize_filename(file.filename or "upload.zip")
        if not safe_name.endswith(".zip"):
            safe_name += ".zip"

        # Stream con límite de tamaño (evita cargar todo el archivo en RAM)
        written = 0
        with open(zip_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    os.remove(zip_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"El archivo supera el límite de {settings.APP_MAX_UPLOAD_SIZE_MB} MB.",
                    )
                f.write(chunk)

        service = ProjectService(db)
        result = await service.process_upload(project_id, zip_path, project_dir)
        return {"message": "Archivos procesados correctamente", **result}
    except ValidationException as e:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/{project_id}/files", response_model=List[ArchivoResponse])
async def get_project_files(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    await ensure_project_access(db, project_id, current_user)
    return await service.list_files_meta(project_id)


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = ProjectService(db)
    await ensure_project_access(db, project_id, current_user)
    return await service.get_project_stats(project_id)
