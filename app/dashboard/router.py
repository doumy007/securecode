from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.dependencies import get_current_active_user, require_role
from app.auth.models import Usuario
from app.dashboard.__init__ import DashboardService

router = APIRouter()


@router.get("/kpi")
async def get_dashboard_kpi(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = DashboardService(db)
    is_admin = await service._is_admin_role(current_user.id)
    if is_admin or current_user.id == 1:
        return await service.get_kpi()
    return await service.get_kpi(current_user.id)


@router.get("/vulnerabilities-by-severity")
async def get_vuln_by_severity(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = DashboardService(db)
    is_admin = await service._is_admin_role(current_user.id)
    if is_admin:
        return await service.get_vulnerability_by_severity()
    return await service.get_vulnerability_by_severity(current_user.id)


@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = DashboardService(db)
    is_admin = await service._is_admin_role(current_user.id)
    if is_admin:
        return await service.get_trends()
    return await service.get_trends(current_user.id)


@router.get("/compliance-radar")
async def get_compliance_radar(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    service = DashboardService(db)
    return await service.get_compliance_radar()
