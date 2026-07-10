from abc import ABC, abstractmethod
from typing import Optional
from app.audits.models import Auditoria
from app.projects.models import Proyecto, ArchivoProyecto


class BaseWorker(ABC):
    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    async def run(self, audit: Auditoria, project: Proyecto, files: list[ArchivoProyecto]) -> dict:
        pass

    def _build_result(self, vulnerabilities: list, summary: Optional[dict] = None) -> dict:
        return {
            "worker": self.name,
            "vulnerabilities": vulnerabilities,
            "summary": summary or {},
            "total": len(vulnerabilities),
        }
