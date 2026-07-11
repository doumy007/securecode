from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
import logging
from typing import Optional

logger = logging.getLogger("securecode.ai")


class OpenAIClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat_completion(self, messages: list, temperature: Optional[float] = None) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=temperature or self.temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise

    async def combined_analysis(self, vuln_data: dict) -> dict:
        from app.ai.prompts import COMBINED_ANALYSIS_PROMPT
        messages = [
            {"role": "system", "content": COMBINED_ANALYSIS_PROMPT},
            {"role": "user", "content": f"Analiza esta vulnerabilidad:\n{vuln_data}"},
        ]
        result = await self.chat_completion(messages)
        return self._parse_json_response(result)

    async def chat_with_context(self, question: str, audit_context: dict) -> str:
        messages = [
            {"role": "system", "content": "Eres un experto en ciberseguridad y compliance. "
             "Responde preguntas sobre el análisis de seguridad del proyecto. "
             "Usa el contexto proporcionado para dar respuestas específicas y accionables."},
            {"role": "user", "content": f"Contexto de la auditoría:\n{audit_context}\n\nPregunta: {question}"},
        ]
        return await self.chat_completion(messages)

    async def generate_report_summary(self, audit_data: dict) -> str:
        messages = [
            {"role": "system", "content": "Genera un resumen ejecutivo profesional de auditoría de seguridad."},
            {"role": "user", "content": f"Genera resumen ejecutivo de:\n{audit_data}"},
        ]
        return await self.chat_completion(messages)

    def _parse_json_response(self, text: str) -> dict:
        import json
        import re
        try:
            json_match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return {"raw_response": text}
