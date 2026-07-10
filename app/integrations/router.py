from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.dependencies import get_current_active_user
from app.auth.models import Usuario
from app.integrations.__init__ import GitHubIntegration, GitLabIntegration, AzureDevOpsIntegration, JiraIntegration
from app.audits.service import AuditService
from app.projects.service import ProjectService
from app.config import settings

router = APIRouter()
github = GitHubIntegration()
gitlab = GitLabIntegration()
azure = AzureDevOpsIntegration()
jira = JiraIntegration()


@router.post("/github/webhook")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    result = await github.handle_webhook(payload)
    if result.get("trigger_audit"):
        service = AuditService(db)
        project_service = ProjectService(db)
        projects = await project_service.get_all_projects()
        for p in projects:
            if p.repo_url and result.get("repo", "") in p.repo_url:
                audit = await service.create_audit(p.id, p.user_id)
                await service.run_audit_async(audit.id)
                return {"message": "Auditoría iniciada", "audit_id": audit.id, **result}
    return result


@router.post("/gitlab/webhook")
async def gitlab_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    result = await gitlab.handle_webhook(payload)
    return result


@router.post("/azure/webhook")
async def azure_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    result = await azure.handle_webhook(payload)
    return result


@router.post("/jira/ticket")
async def create_jira_ticket(
    vuln_id: int,
    project_key: str = "SEC",
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user),
):
    from app.audits.service import AuditService
    audit_service = AuditService(db)
    vuln = await audit_service.get_vulnerability(vuln_id)

    ticket = await jira.create_ticket({
        "nombre": vuln.nombre,
        "severidad": vuln.severidad,
        "archivo": vuln.archivo.ruta if vuln.archivo else "",
        "recomendacion": vuln.recomendacion,
    }, project_key)

    return ticket
