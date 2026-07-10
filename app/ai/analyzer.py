import logging
from app.ai.openai_client import OpenAIClient
from app.ai.prompts import ACTION_PLAN_PROMPT

logger = logging.getLogger("securecode.ai")


class AIAnalyzer:
    def __init__(self):
        self.client = OpenAIClient()

    async def analyze_vulnerabilities(self, findings: list) -> dict:
        if not findings:
            return {"analysis": [], "action_plan": {}}

        results = {"analysis": [], "action_plan": {}, "compliance": []}

        for finding in findings:
            try:
                analysis = await self.client.analyze_vulnerability(finding)
                results["analysis"].append(analysis)

                fix = await self.client.generate_fix(finding)
                finding["codigo_corregido"] = fix.get("codigo_corregido", "")

                compliance = await self.client.analyze_compliance(finding)
                results["compliance"].append(compliance)

                vuln_type = finding.get("tipo", "unknown")
                if vuln_type not in results["action_plan"]:
                    plan = await self._generate_action_plan(finding)
                    results["action_plan"][vuln_type] = plan

            except Exception as e:
                logger.error(f"Error analyzing finding: {e}")
                continue

        return results

    async def _generate_action_plan(self, finding: dict) -> list:
        try:
            from app.ai.openai_client import OpenAIClient
            client = OpenAIClient()
            messages = [
                {"role": "system", "content": ACTION_PLAN_PROMPT},
                {"role": "user", "content": f"Genera plan para: {finding}"},
            ]
            result = await client.chat_completion(messages)
            return client._parse_json_response(result).get("plan", [])
        except Exception as e:
            logger.error(f"Error generating action plan: {e}")
            return []
