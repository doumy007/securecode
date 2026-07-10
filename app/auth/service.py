from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import pyotp
import qrcode
import base64
from io import BytesIO

from app.config import settings
from app.auth.models import Usuario, Rol
from app.exceptions import UnauthorizedException, NotFoundException, ConflictException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_roles_if_not_exist(self):
        roles_data = [
            ("admin", "Administrador del sistema", ["*"]),
            ("auditor", "Auditor de seguridad", ["audits:read", "audits:write", "reports:read"]),
            ("developer", "Desarrollador", ["projects:read", "projects:write", "audits:read"]),
            ("jefe_ti", "Jefe de TI", ["projects:read", "audits:read", "reports:read", "dashboard:read"]),
            ("cliente", "Cliente externo", ["projects:read", "audits:read", "reports:read"]),
        ]
        for nombre, descripcion, permisos in roles_data:
            result = await self.db.execute(select(Rol).where(Rol.nombre == nombre))
            if not result.scalar_one_or_none():
                rol = Rol(nombre=nombre, descripcion=descripcion, permisos=permisos)
                self.db.add(rol)
        await self.db.commit()

    async def register_user(self, username: str, email: str, password: str, nombre_completo: Optional[str] = None, rol_id: Optional[int] = None) -> Usuario:
        result = await self.db.execute(select(Usuario).where(
            (Usuario.username == username) | (Usuario.email == email)
        ))
        if result.scalar_one_or_none():
            raise ConflictException("El usuario o email ya existe")

        if not rol_id:
            result = await self.db.execute(select(Rol).where(Rol.nombre == "developer"))
            rol = result.scalar_one_or_none()
            if not rol:
                raise NotFoundException("Rol por defecto no encontrado")
            rol_id = rol.id

        hashed = pwd_context.hash(password)
        user = Usuario(
            username=username,
            email=email,
            password_hash=hashed,
            nombre_completo=nombre_completo,
            rol_id=rol_id,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        result = await self.db.execute(
            select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.id == user.id)
        )
        user = result.scalar_one_or_none()
        return user

    async def authenticate_user(self, username: str, password: str) -> Usuario:
        result = await self.db.execute(
            select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise UnauthorizedException("Credenciales inválidas")
        if not pwd_context.verify(password, user.password_hash):
            raise UnauthorizedException("Credenciales inválidas")
        if not user.activo:
            raise UnauthorizedException("Usuario inactivo")

        user.ultimo_login = datetime.utcnow()
        await self.db.commit()
        return user

    async def verify_access_token(self, token: str) -> Optional[Usuario]:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id: int = int(payload.get("sub"))
            if user_id is None:
                return None
        except JWTError:
            return None

        result = await self.db.execute(
            select(Usuario).options(selectinload(Usuario.rol)).where(Usuario.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user

    def create_access_token(self, user: Usuario, rol_name: Optional[str] = None) -> str:
        expires = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "rol": rol_name or (user.rol.nombre if user.rol else "unknown"),
            "exp": expires,
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def create_refresh_token(self, user: Usuario) -> str:
        expires = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user.id,
            "exp": expires,
            "iat": datetime.utcnow(),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async def refresh_access_token(self, refresh_token: str) -> str:
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Token inválido")
            user_id = payload.get("sub")
            result = await self.db.execute(select(Usuario).where(Usuario.id == user_id))
            user = result.scalar_one_or_none()
            if not user or not user.activo:
                raise UnauthorizedException("Usuario no encontrado o inactivo")
            return self.create_access_token(user)
        except JWTError:
            raise UnauthorizedException("Token de refresco inválido o expirado")

    def setup_mfa(self, user: Usuario) -> dict:
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name=settings.MFA_ISSUER_NAME)

        qr = qrcode.make(uri)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "uri": uri,
        }

    def verify_mfa_token(self, user: Usuario, token: str) -> bool:
        if not user.mfa_secret:
            return False
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token)

    async def change_password(self, user: Usuario, current_password: str, new_password: str) -> bool:
        if not pwd_context.verify(current_password, user.password_hash):
            raise UnauthorizedException("Contraseña actual incorrecta")
        user.password_hash = pwd_context.hash(new_password)
        await self.db.commit()
        return True

    async def get_users(self, skip: int = 0, limit: int = 100) -> list[Usuario]:
        result = await self.db.execute(select(Usuario).offset(skip).limit(limit))
        return result.scalars().all()

    async def get_user_by_id(self, user_id: int) -> Usuario:
        result = await self.db.execute(select(Usuario).where(Usuario.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("Usuario no encontrado")
        return user
