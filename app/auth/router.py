from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.service import AuthService
from app.auth.schemas import (
    UsuarioCreate, UsuarioResponse, TokenResponse, LoginRequest,
    MFASetupResponse, MFAVerifyRequest, MFAVerifyResponse,
    RefreshTokenRequest, ChangePasswordRequest, UsuarioUpdate,
    UsuarioUpdateAdmin, RolCreate, RolUpdate, RolResponse,
)
from app.dependencies import get_current_active_user, require_role, require_permission
from app.auth.models import Usuario
from app.config import settings
from app.shared.rate_limit import LoginRateLimiter

router = APIRouter()

_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_MINUTES * 60,
)


def _client_ip(request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.create_roles_if_not_exist()
    # IMPORTANTE: el rol_id enviado por el cliente se ignora por completo
    # (evita escalada de privilegios). Los nuevos usuarios usan el rol por defecto.
    user = await service.register_user(
        username=data.username,
        email=data.email,
        password=data.password,
        nombre_completo=data.nombre_completo,
        rol_id=None,
    )
    return user


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_initial_data(db: AsyncSession = Depends(get_db)):
    # Endpoint solo disponible si se habilita explícitamente vía SEED_ADMIN_ENABLED=true
    if not settings.SEED_ADMIN_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
    service = AuthService(db)
    await service.create_roles_if_not_exist()
    try:
        user = await service.register_user(
            username="admin",
            email="admin@securecode.ai",
            password="Admin123!",
            nombre_completo="Administrador",
            rol_id=1,
        )
        return {"message": "Admin user created", "username": user.username}
    except Exception as e:
        from app.exceptions import ConflictException
        if isinstance(e, ConflictException):
            return {"message": "Admin user already exists"}
        raise


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    if not _limiter.check(data.username, ip):
        retry_after = settings.LOGIN_WINDOW_MINUTES * 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Espera {settings.LOGIN_WINDOW_MINUTES} min.",
            headers={"Retry-After": str(retry_after)},
        )
    service = AuthService(db)
    try:
        user = await service.authenticate_user(data.username, data.password)
    except Exception:
        _limiter.record_failure(data.username, ip)
        raise
    _limiter.reset(data.username, ip)
    access_token = service.create_access_token(user, rol_name=user.rol.nombre if user.rol else "unknown")
    refresh_token = service.create_refresh_token(user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    new_access_token = await service.refresh_access_token(data.refresh_token)
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=data.refresh_token,
        expires_in=30,
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: Usuario = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = service.setup_mfa(current_user)
    await db.commit()
    return result


@router.post("/mfa/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    data: MFAVerifyRequest,
    current_user: Usuario = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    verified = service.verify_mfa_token(current_user, data.token)
    if not verified:
        raise HTTPException(status_code=400, detail="Token MFA inválido")
    current_user.mfa_enabled = True
    await db.commit()
    return MFAVerifyResponse(verified=True, recovery_codes=[])


@router.get("/me", response_model=UsuarioResponse)
async def get_me(
    current_user: Usuario = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.auth.models import Rol
    result = await db.execute(select(Rol.nombre).where(Rol.id == current_user.rol_id))
    row = result.scalar_one_or_none()
    current_user.rol_nombre = row or "—"
    return current_user


@router.put("/me", response_model=UsuarioResponse)
async def update_me(
    data: UsuarioUpdate,
    current_user: Usuario = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if data.nombre_completo:
        current_user.nombre_completo = data.nombre_completo
    if data.email:
        current_user.email = data.email
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: Usuario = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.change_password(current_user, data.current_password, data.new_password)
    return {"message": "Contraseña actualizada correctamente"}


@router.get("/users", response_model=list[UsuarioResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    return await service.get_users(skip, limit)


@router.get("/users/{user_id}", response_model=UsuarioResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    return await service.get_user_by_id(user_id)


@router.post("/users", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    user = await service.register_user(
        username=data.username,
        email=data.email,
        password=data.password,
        nombre_completo=data.nombre_completo,
        rol_id=data.rol_id,
    )
    return user


@router.put("/users/{user_id}", response_model=UsuarioResponse)
async def admin_update_user(
    user_id: int,
    data: UsuarioUpdateAdmin,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    return await service.update_user(user_id, data.model_dump(exclude_none=True))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    await service.delete_user(user_id)


@router.get("/roles", response_model=list[RolResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    return await service.get_roles()


@router.post("/roles", response_model=RolResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    return await service.create_role(nombre=data.nombre, descripcion=data.descripcion, permisos=data.permisos)


@router.put("/roles/{role_id}", response_model=RolResponse)
async def update_role(
    role_id: int,
    data: RolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    return await service.update_role(role_id, data.model_dump(exclude_none=True))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    service = AuthService(db)
    await service.delete_role(role_id)
