from app.ai.openai_client import OpenAIClient
import logging

logger = logging.getLogger("securecode.ai")


class FixGenerator:
    def __init__(self):
        self.client = OpenAIClient()

    async def generate_fix(self, vuln_data: dict) -> dict:
        return await self.client.generate_fix(vuln_data)

    async def generate_bulk_fixes(self, vulnerabilities: list) -> list:
        fixes = []
        for vuln in vulnerabilities:
            try:
                fix = await self.generate_fix(vuln)
                fixes.append(fix)
            except Exception as e:
                logger.error(f"Error generating fix: {e}")
                fixes.append({
                    "codigo_vulnerable": vuln.get("codigo_vulnerable", ""),
                    "codigo_corregido": "Error generando corrección automática",
                    "explicacion": f"Error: {str(e)}",
                })
        return fixes
