from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
import datetime
import enum
from app.database import Base


class EstadoAuditoria(str, enum.Enum):
    PENDIENTE = "pendiente"
    EJECUTANDO = "ejecutando"
    COMPLETADA = "completada"
    FALLIDA = "fallida"


class Severidad(str, enum.Enum):
    CRITICA = "crítica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class Auditoria(Base):
    __tablename__ = "sc_auditorias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proyecto_id = Column(Integer, ForeignKey("sc_proyectos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("sc_usuarios.id"), nullable=False)
    nombre = Column(String(255))
    estado = Column(String(20), default=EstadoAuditoria.PENDIENTE.value)
    tipo = Column(String(20), default="automática")
    version = Column(String(50))
    resultado_resumen = Column(JSON)
    frameworks = Column(JSON)
    git_url = Column(String(1024))
    git_username = Column(String(255))
    git_token = Column(String(512))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)

    proyecto = relationship("Proyecto", back_populates="auditorias")
    usuario = relationship("Usuario", back_populates="auditorias")
    resultados_workers = relationship("ResultadoWorker", back_populates="auditoria", cascade="all, delete-orphan")
    vulnerabilidades = relationship("Vulnerabilidad", back_populates="auditoria", cascade="all, delete-orphan")
    tareas_remediacion = relationship("TareaRemediacion", back_populates="auditoria", cascade="all, delete-orphan")
    historial = relationship("HistorialEjecucion", back_populates="auditoria", cascade="all, delete-orphan")


class ResultadoWorker(Base):
    __tablename__ = "sc_resultados_worker"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditoria_id = Column(Integer, ForeignKey("sc_auditorias.id"), nullable=False)
    worker = Column(String(100), nullable=False)
    estado = Column(String(20), default="pendiente")
    resultado = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    auditoria = relationship("Auditoria", back_populates="resultados_workers")


class Vulnerabilidad(Base):
    __tablename__ = "sc_vulnerabilidades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditoria_id = Column(Integer, ForeignKey("sc_auditorias.id"), nullable=False)
    archivo_id = Column(Integer, ForeignKey("sc_archivos_proyecto.id"), nullable=True)
    tipo = Column(String(100), nullable=False)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text)
    severidad = Column(String(20), default=Severidad.MEDIA.value)
    cvss_score = Column(Float)
    impacto = Column(String(20))
    probabilidad = Column(String(20))
    prioridad = Column(String(20))
    linea_inicio = Column(Integer)
    linea_fin = Column(Integer)
    codigo_vulnerable = Column(Text)
    codigo_corregido = Column(Text)
    recomendacion = Column(Text)
    fuente = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resuelta = Column(String(20), default="pendiente")

    auditoria = relationship("Auditoria", back_populates="vulnerabilidades")
    archivo = relationship("ArchivoProyecto")
    mapeos = relationship("MapeoEstandar", back_populates="vulnerabilidad", cascade="all, delete-orphan")
    tareas = relationship("TareaRemediacion", back_populates="vulnerabilidad", cascade="all, delete-orphan")


class MapeoEstandar(Base):
    __tablename__ = "sc_mapeo_estandares"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vulnerabilidad_id = Column(Integer, ForeignKey("sc_vulnerabilidades.id"), nullable=False)
    estandar = Column(String(100), nullable=False)
    categoria = Column(String(100))
    referencia = Column(String(255))
    descripcion = Column(Text)

    vulnerabilidad = relationship("Vulnerabilidad", back_populates="mapeos")


class TareaRemediacion(Base):
    __tablename__ = "sc_tareas_remediacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditoria_id = Column(Integer, ForeignKey("sc_auditorias.id"), nullable=False)
    vulnerabilidad_id = Column(Integer, ForeignKey("sc_vulnerabilidades.id"), nullable=True)
    paso = Column(Integer)
    descripcion = Column(Text)
    archivo = Column(String(1024))
    metodo = Column(String(255))
    prioridad = Column(String(20))
    estado = Column(String(20), default="pendiente")
    user_id = Column(Integer, ForeignKey("sc_usuarios.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    auditoria = relationship("Auditoria", back_populates="tareas_remediacion")
    vulnerabilidad = relationship("Vulnerabilidad", back_populates="tareas")


class HistorialEjecucion(Base):
    __tablename__ = "sc_historial_ejecuciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditoria_id = Column(Integer, ForeignKey("sc_auditorias.id"), nullable=False)
    evento = Column(String(255), nullable=False)
    detalle = Column(JSON)
    auditoria = relationship("Auditoria", back_populates="historial")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
