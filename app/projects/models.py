from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import datetime
import enum
from app.database import Base


class EstadoProyecto(str, enum.Enum):
    ACTIVO = "activo"
    ARCHIVADO = "archivado"
    EN_REVISION = "en_revision"


class TipoRepositorio(str, enum.Enum):
    ZIP = "zip"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class Lenguaje(str, enum.Enum):
    JAVA = "Java"
    PYTHON = "Python"
    DOTNET = ".NET"
    NODE = "Node"
    ANGULAR = "Angular"
    REACT = "React"
    PHP = "PHP"
    GO = "Go"
    UNKNOWN = "Unknown"


class Framework(str, enum.Enum):
    SPRING_BOOT = "Spring Boot"
    DJANGO = "Django"
    FLASK = "Flask"
    FASTAPI = "FastAPI"
    EXPRESS = "Express"
    DOTNET_CORE = ".NET Core"
    ANGULAR = "Angular"
    REACT = "React"
    LARAVEL = "Laravel"
    GIN = "Gin"
    UNKNOWN = "Unknown"


class Proyecto(Base):
    __tablename__ = "sc_proyectos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False, index=True)
    descripcion = Column(Text)
    lenguaje = Column(String(50), default=Lenguaje.UNKNOWN.value)
    framework = Column(String(50), default=Framework.UNKNOWN.value)
    repo_url = Column(String(1024))
    repo_tipo = Column(String(20), default=TipoRepositorio.ZIP.value)
    estado = Column(String(20), default=EstadoProyecto.ACTIVO.value)
    version_actual = Column(String(50), default="1.0.0")
    user_id = Column(Integer, ForeignKey("sc_usuarios.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    usuario = relationship("Usuario", back_populates="proyectos")
    archivos = relationship("ArchivoProyecto", back_populates="proyecto", cascade="all, delete-orphan")
    auditorias = relationship("Auditoria", back_populates="proyecto", cascade="all, delete-orphan")


class ArchivoProyecto(Base):
    __tablename__ = "sc_archivos_proyecto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proyecto_id = Column(Integer, ForeignKey("sc_proyectos.id"), nullable=False)
    ruta = Column(String(1024), nullable=False)
    hash = Column(String(64))
    tamano = Column(Integer)
    lenguaje = Column(String(50))
    contenido = Column(Text)

    proyecto = relationship("Proyecto", back_populates="archivos")
