from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.service import AuthService
from app.auth.models import Usuario
from typing import Optional

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    token = credentials.credentials
    auth_service = AuthService(db)
    user = await auth_service.verify_access_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )
    return current_user


def require_role(*roles: str):
    async def role_checker(current_user: Usuario = Depends(get_current_active_user)):
        if current_user.rol.nombre not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(roles)}",
            )
        return current_user
    return role_checker


def require_permission(*permissions: str):
    async def perm_checker(current_user: Usuario = Depends(get_current_active_user)):
        user_perms = current_user.rol.permisos or []
        if "*" in user_perms:
            return current_user
        for perm in permissions:
            if perm not in user_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permiso requerido: {perm}",
                )
        return current_user
    return perm_checker


async def ensure_project_access(db: AsyncSession, project_id: int, user: Usuario) -> None:
    """IDOR: solo el propietario (o admin) puede acceder al proyecto."""
    if user.rol.nombre == "admin":
        return
    from sqlalchemy import select
    from app.projects.models import Proyecto
    from app.exceptions import NotFoundException
    result = await db.execute(select(Proyecto).where(Proyecto.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException("Proyecto no encontrado")
    if project.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este proyecto",
        )


async def ensure_audit_access(db: AsyncSession, audit_id: int, user: Usuario) -> None:
    """IDOR: solo el propietario (o admin) puede acceder a la auditoría."""
    if user.rol.nombre == "admin":
        return
    from sqlalchemy import select
    from app.audits.models import Auditoria
    from app.exceptions import NotFoundException
    result = await db.execute(select(Auditoria).where(Auditoria.id == audit_id))
    audit = result.scalar_one_or_none()
    if not audit:
        raise NotFoundException("Auditoría no encontrada")
    if audit.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta auditoría",
        )
