from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    permisos: list = []

    class Config:
        from_attributes = True


class UsuarioCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    nombre_completo: Optional[str] = None
    rol_id: Optional[int] = None


class UsuarioResponse(BaseModel):
    id: int
    username: str
    email: str
    nombre_completo: Optional[str] = None
    activo: bool
    mfa_enabled: bool
    rol: RolResponse
    rol_nombre: Optional[str] = None
    permisos: list = []
    ultimo_login: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str
    uri: str


class MFAVerifyRequest(BaseModel):
    token: str


class MFAVerifyResponse(BaseModel):
    verified: bool
    recovery_codes: Optional[List[str]] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[str] = None


class UsuarioUpdateAdmin(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[str] = None
    activo: Optional[bool] = None
    rol_id: Optional[int] = None


class RolCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    descripcion: Optional[str] = None
    permisos: List[str] = []


class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    permisos: Optional[List[str]] = None
