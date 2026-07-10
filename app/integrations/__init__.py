import hmac
import hashlib
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("securecode.integrations")


class GitHubIntegration:
    async def handle_webhook(self, payload: dict, signature: Optional[str] = None) -> dict:
        event = payload.get("x-github-event", "push")
        repo = payload.get("repository", {}).get("full_name", "unknown")

        if event == "push":
            branch = payload.get("ref", "").replace("refs/heads/", "")
            logger.info(f"Push recibido en {repo}/{branch}")
            return {
                "event": event,
                "repo": repo,
                "branch": branch,
                "action": "trigger_audit",
            }
        elif event == "pull_request":
            action = payload.get("action", "")
            pr_number = payload.get("number", 0)
            logger.info(f"PR #{pr_number} {action} en {repo}")
            if action in ("opened", "synchronize"):
                return {
                    "event": event,
                    "repo": repo,
                    "pr_number": pr_number,
                    "action": action,
                    "trigger_audit": True,
                }

        return {"event": event, "repo": repo, "action": "no_action"}

    def verify_signature(self, payload_body: bytes, signature_header: str, secret: str) -> bool:
        if not signature_header:
            return False
        expected_sig = "sha256=" + hmac.new(
            secret.encode(), payload_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature_header)


class GitLabIntegration:
    async def handle_webhook(self, payload: dict) -> dict:
        event = payload.get("object_kind", "push")
        repo = payload.get("project", {}).get("path_with_namespace", "unknown")

        if event == "push":
            branch = payload.get("ref", "").replace("refs/heads/", "")
            return {"event": event, "repo": repo, "branch": branch, "trigger_audit": True}

        return {"event": event, "repo": repo, "action": "no_action"}


class AzureDevOpsIntegration:
    async def handle_webhook(self, payload: dict) -> dict:
        event_type = payload.get("eventType", "")
        resource = payload.get("resource", {})
        repo = resource.get("repository", {}).get("name", "unknown")

        if "git.push" in event_type:
            return {"event": "push", "repo": repo, "trigger_audit": True}
        elif "git.pullrequest" in event_type:
            return {"event": "pull_request", "repo": repo, "trigger_audit": True}

        return {"event": event_type, "repo": repo, "action": "no_action"}


class JiraIntegration:
    async def create_ticket(self, vulnerability: dict, project_key: str = "SEC") -> dict:
        try:
            import json as json_module
            logger.info(f"Creando ticket Jira para vulnerabilidad: {vulnerability.get('nombre')}")
            return {
                "success": True,
                "ticket_id": f"{project_key}-{hash(str(vulnerability)) % 10000}",
                "summary": f"[SecureCode] {vulnerability.get('nombre', 'Vulnerabilidad')}",
                "priority": vulnerability.get("severidad", "medium"),
            }
        except Exception as e:
            logger.error(f"Error creando ticket Jira: {e}")
            return {"success": False, "error": str(e)}
