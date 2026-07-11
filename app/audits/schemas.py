from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AuditoriaCreate(BaseModel):
    proyecto_id: int
    nombre: Optional[str] = None
    frameworks: Optional[List[str]] = None
    git_url: Optional[str] = None
    git_username: Optional[str] = None
    git_token: Optional[str] = None


class AuditoriaResponse(BaseModel):
    id: int
    proyecto_id: int
    user_id: int
    nombre: Optional[str] = None
    estado: str
    tipo: Optional[str] = None
    version: Optional[str] = None
    resultado_resumen: Optional[dict] = None
    frameworks: Optional[list] = None
    git_url: Optional[str] = None
    git_username: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    vulnerabilities_count: Optional[int] = None
    proyecto_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class VulnerabilidadResponse(BaseModel):
    id: int
    auditoria_id: int
    archivo_id: Optional[int] = None
    tipo: str
    nombre: str
    descripcion: Optional[str] = None
    severidad: Optional[str] = None
    cvss_score: Optional[float] = None
    impacto: Optional[str] = None
    probabilidad: Optional[str] = None
    prioridad: Optional[str] = None
    linea_inicio: Optional[int] = None
    linea_fin: Optional[int] = None
    codigo_vulnerable: Optional[str] = None
    codigo_corregido: Optional[str] = None
    recomendacion: Optional[str] = None
    fuente: Optional[str] = None
    resuelta: Optional[str] = None
    created_at: Optional[datetime] = None
    mapeos: Optional[List[dict]] = None
    tareas: Optional[List[dict]] = None
    archivo_ruta: Optional[str] = None

    class Config:
        from_attributes = True


class MapeoEstandarResponse(BaseModel):
    id: int
    estandar: str
    categoria: Optional[str] = None
    referencia: Optional[str] = None
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True


class TareaRemediacionResponse(BaseModel):
    id: int
    paso: Optional[int] = None
    descripcion: Optional[str] = None
    archivo: Optional[str] = None
    metodo: Optional[str] = None
    prioridad: Optional[str] = None
    estado: Optional[str] = None

    class Config:
        from_attributes = True


class AuditoriaSummary(BaseModel):
    total_audits: int
    completed: int
    failed: int
    pending: int
    running: int
    total_vulnerabilities: int
    critical: int
    high: int
    medium: int
    low: int
    avg_compliance_score: Optional[float] = None
