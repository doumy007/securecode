from app.ai.openai_client import OpenAIClient
import logging

logger = logging.getLogger("securecode.ai")


class AuditChat:
    def __init__(self):
        self.client = OpenAIClient()
        self.conversations = {}

    async def ask(self, audit_id: int, question: str, audit_context: dict) -> str:
        conversation_key = f"audit_{audit_id}"

        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = {
                "history": [],
                "context": audit_context,
            }

        conv = self.conversations[conversation_key]
        conv["history"].append({"role": "user", "content": question})

        response = await self.client.chat_with_context(question, audit_context)

        conv["history"].append({"role": "assistant", "content": response})

        if len(conv["history"]) > 20:
            conv["history"] = conv["history"][-20:]

        return response

    def clear_history(self, audit_id: int):
        self.conversations.pop(f"audit_{audit_id}", None)
