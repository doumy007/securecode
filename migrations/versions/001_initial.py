"""initial migration with sc_ prefix

Revision ID: 001
Revises: 
Create Date: 2026-07-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sc_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(50), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column("permisos", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )

    op.create_table(
        "sc_usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("nombre_completo", sa.String(255), nullable=True),
        sa.Column("rol_id", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), default=True),
        sa.Column("mfa_secret", sa.String(64), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), default=False),
        sa.Column("ultimo_login", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["rol_id"], ["sc_roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "sc_proyectos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("lenguaje", sa.String(50), nullable=True),
        sa.Column("framework", sa.String(50), nullable=True),
        sa.Column("repo_url", sa.String(1024), nullable=True),
        sa.Column("repo_tipo", sa.String(20), nullable=True),
        sa.Column("estado", sa.String(20), nullable=True),
        sa.Column("version_actual", sa.String(50), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["sc_usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_archivos_proyecto",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("proyecto_id", sa.Integer(), nullable=False),
        sa.Column("ruta", sa.String(1024), nullable=False),
        sa.Column("hash", sa.String(64), nullable=True),
        sa.Column("tamano", sa.Integer(), nullable=True),
        sa.Column("lenguaje", sa.String(50), nullable=True),
        sa.Column("contenido", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["proyecto_id"], ["sc_proyectos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_auditorias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("proyecto_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("resultado_resumen", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["proyecto_id"], ["sc_proyectos.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["sc_usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_resultados_worker",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("auditoria_id", sa.Integer(), nullable=False),
        sa.Column("worker", sa.String(100), nullable=False),
        sa.Column("estado", sa.String(20), nullable=True),
        sa.Column("resultado", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["auditoria_id"], ["sc_auditorias.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_vulnerabilidades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("auditoria_id", sa.Integer(), nullable=False),
        sa.Column("archivo_id", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("severidad", sa.String(20), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("impacto", sa.String(20), nullable=True),
        sa.Column("probabilidad", sa.String(20), nullable=True),
        sa.Column("prioridad", sa.String(20), nullable=True),
        sa.Column("linea_inicio", sa.Integer(), nullable=True),
        sa.Column("linea_fin", sa.Integer(), nullable=True),
        sa.Column("codigo_vulnerable", sa.Text(), nullable=True),
        sa.Column("codigo_corregido", sa.Text(), nullable=True),
        sa.Column("recomendacion", sa.Text(), nullable=True),
        sa.Column("fuente", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("resuelta", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["archivo_id"], ["sc_archivos_proyecto.id"]),
        sa.ForeignKeyConstraint(["auditoria_id"], ["sc_auditorias.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_mapeo_estandares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vulnerabilidad_id", sa.Integer(), nullable=False),
        sa.Column("estandar", sa.String(100), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column("referencia", sa.String(255), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["vulnerabilidad_id"], ["sc_vulnerabilidades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_tareas_remediacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("auditoria_id", sa.Integer(), nullable=False),
        sa.Column("vulnerabilidad_id", sa.Integer(), nullable=True),
        sa.Column("paso", sa.Integer(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("archivo", sa.String(1024), nullable=True),
        sa.Column("metodo", sa.String(255), nullable=True),
        sa.Column("prioridad", sa.String(20), nullable=True),
        sa.Column("estado", sa.String(20), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["auditoria_id"], ["sc_auditorias.id"]),
        sa.ForeignKeyConstraint(["vulnerabilidad_id"], ["sc_vulnerabilidades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sc_historial_ejecuciones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("auditoria_id", sa.Integer(), nullable=False),
        sa.Column("evento", sa.String(255), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["auditoria_id"], ["sc_auditorias.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sc_historial_ejecuciones")
    op.drop_table("sc_tareas_remediacion")
    op.drop_table("sc_mapeo_estandares")
    op.drop_table("sc_vulnerabilidades")
    op.drop_table("sc_resultados_worker")
    op.drop_table("sc_auditorias")
    op.drop_table("sc_archivos_proyecto")
    op.drop_table("sc_proyectos")
    op.drop_table("sc_usuarios")
    op.drop_table("sc_roles")
