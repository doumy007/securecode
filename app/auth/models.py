from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
import datetime
from app.database import Base


class Rol(Base):
    __tablename__ = "sc_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), unique=True, nullable=False, index=True)
    descripcion = Column(String(255))
    permisos = Column(JSON, default=list)

    usuarios = relationship("Usuario", back_populates="rol")


class Usuario(Base):
    __tablename__ = "sc_usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nombre_completo = Column(String(255))
    rol_id = Column(Integer, ForeignKey("sc_roles.id"), nullable=False)
    activo = Column(Boolean, default=True)
    mfa_secret = Column(String(64))
    mfa_enabled = Column(Boolean, default=False)
    ultimo_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    rol = relationship("Rol", back_populates="usuarios")
    proyectos = relationship("Proyecto", back_populates="usuario")
    auditorias = relationship("Auditoria", back_populates="usuario")


# Late imports so string-based relationships in Usuario resolve correctly
from app.projects.models import Proyecto  # noqa: E402, F811
from app.audits.models import Auditoria  # noqa: E402, F811
