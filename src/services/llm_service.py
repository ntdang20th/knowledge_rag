from typing import AsyncIterator

from src.infrastructure.ollama.client import OllamaClient

SYSTEM_PROMPT = """You are a knowledgeable assistant for a software development team. You answer questions about work items, pull requests, sprints, and team activity based on data from Azure DevOps.

Answer the user's question using ONLY the context provided below. If the context does not contain enough information to answer, say so clearly.

When referencing specific items, always include their ID (e.g., "Work Item #1234" or "PR #567").
Indicate confidence level when the context is sparse.

CONTEXT:
{context}"""


class LLMService:
    def __init__(self, ollama: OllamaClient):
        self._ollama = ollama

    async def generate_answer(self, question: str, context: str) -> str:
        system = SYSTEM_PROMPT.format(context=context)
        return await self._ollama.generate(prompt=question, system=system)

    async def generate_answer_stream(
        self, question: str, context: str
    ) -> AsyncIterator[str]:
        system = SYSTEM_PROMPT.format(context=context)
        async for token in self._ollama.generate_stream(prompt=question, system=system):
            yield token
