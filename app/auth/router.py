from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.auth.service import AuthService
from app.auth.schemas import (
    UsuarioCreate, UsuarioResponse, TokenResponse, LoginRequest,
    MFASetupResponse, MFAVerifyRequest, MFAVerifyResponse,
    RefreshTokenRequest, ChangePasswordRequest, UsuarioUpdate,
)
from app.dependencies import get_current_active_user, require_role
from app.auth.models import Usuario

router = APIRouter()


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UsuarioCreate, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.create_roles_if_not_exist()
    user = await service.register_user(
        username=data.username,
        email=data.email,
        password=data.password,
        nombre_completo=data.nombre_completo,
        rol_id=data.rol_id,
    )
    return user


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_initial_data(db: AsyncSession = Depends(get_db)):
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
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    user = await service.authenticate_user(data.username, data.password)
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
