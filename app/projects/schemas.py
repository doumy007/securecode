from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProyectoCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: Optional[str] = None
    repo_url: Optional[str] = None
    repo_tipo: Optional[str] = "zip"


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    lenguaje: Optional[str] = None
    framework: Optional[str] = None


class ProyectoResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    lenguaje: Optional[str] = None
    framework: Optional[str] = None
    repo_url: Optional[str] = None
    repo_tipo: Optional[str] = None
    estado: Optional[str] = None
    version_actual: Optional[str] = None
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archivos_count: Optional[int] = None
    auditorias_count: Optional[int] = None

    class Config:
        from_attributes = True


class ArchivoResponse(BaseModel):
    id: int
    proyecto_id: int
    ruta: str
    hash: Optional[str] = None
    tamano: Optional[int] = None
    lenguaje: Optional[str] = None

    class Config:
        from_attributes = True
