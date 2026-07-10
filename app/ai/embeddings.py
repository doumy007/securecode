import logging
import json
from typing import Optional

logger = logging.getLogger("securecode.ai")


class EmbeddingService:
    def __init__(self):
        self.dimension = 1536
        self.index = {}

    async def create_embedding(self, text: str) -> list[float]:
        try:
            from openai import AsyncOpenAI
            from app.config import settings
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return [0.0] * self.dimension

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import numpy as np
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-10))

    async def find_similar_vulnerabilities(self, query: str, vulns: list, top_k: int = 5) -> list:
        query_embedding = await self.create_embedding(query)
        scored = []

        for vuln in vulns:
            vuln_text = f"{vuln.get('nombre', '')} {vuln.get('descripcion', '')}"
            vuln_embedding = await self.create_embedding(vuln_text)
            score = self.cosine_similarity(query_embedding, vuln_embedding)
            scored.append((score, vuln))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [v for s, v in scored[:top_k]]
