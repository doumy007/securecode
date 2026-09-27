from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.service import AuthService
from app.auth.models import Usuario
from app.shared.cache import cache
from typing import Optional

security = HTTPBearer()

# La BD remota tarda ~0.4-0.6 s por consulta; resolver el usuario por token en
# CADA request (2 consultas: usuario + rol) dominaba el tiempo de toda página.
# Se cachea un SNAPSHOT plano del usuario (no el objeto ORM: Session.close()
# expira los atributos y un objeto desasociado lanza DetachedInstanceError al
# leerlos en otro request). TTL corto: cambios de rol/estado se reflejan en ≤60 s.
AUTH_USER_TTL = 60


class _CachedRol:
    __slots__ = ("id", "nombre", "descripcion", "permisos")

    def __init__(self, id=None, nombre="", descripcion=None, permisos=None):
        self.id = id
        self.nombre = nombre
        self.descripcion = descripcion
        self.permisos = permisos or []


class _CachedUser:
    __slots__ = (
        "id", "username", "email", "password_hash", "nombre_completo", "activo",
        "mfa_secret", "mfa_enabled", "rol_id", "ultimo_login", "created_at",
        "updated_at", "rol", "rol_nombre", "permisos",
    )

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    token = credentials.credentials
    cached = cache.get(f"auth:user:{token}")
    if cached is not None:
        return cached

    auth_service = AuthService(db)
    user = await auth_service.verify_access_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    rol = user.rol
    snapshot = _CachedUser(
        id=user.id,
        username=user.username,
        email=user.email,
        password_hash=user.password_hash,
        nombre_completo=user.nombre_completo,
        activo=user.activo,
        mfa_secret=user.mfa_secret,
        mfa_enabled=user.mfa_enabled,
        rol_id=user.rol_id,
        ultimo_login=user.ultimo_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
        rol=_CachedRol(
            id=rol.id, nombre=rol.nombre, descripcion=rol.descripcion,
            permisos=list(rol.permisos or []) if rol.permisos else [],
        ) if rol else None,
        rol_nombre=getattr(user, "rol_nombre", None) or (rol.nombre if rol else None),
        permisos=list(rol.permisos or []) if rol and rol.permisos else [],
    )
    cache.set(f"auth:user:{token}", snapshot, ttl_seconds=AUTH_USER_TTL)
    return snapshot


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
