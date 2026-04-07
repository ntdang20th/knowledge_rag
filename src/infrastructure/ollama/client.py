from typing import AsyncIterator

import httpx
import structlog

from src.config import settings
from src.core.exceptions import OllamaError

logger = structlog.get_logger()


class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=300.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def is_available(self) -> bool:
        try:
            resp = await self._http.get("/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def list_models(self) -> list[str]:
        try:
            resp = await self._http.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except httpx.HTTPError as e:
            raise OllamaError(f"Failed to list models: {e}") from e

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model = model or settings.ollama_embed_model
        try:
            resp = await self._http.post(
                "/api/embed",
                json={"model": model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]
        except httpx.HTTPError as e:
            raise OllamaError(f"Embedding failed: {e}") from e
        except KeyError:
            raise OllamaError("Unexpected embedding response format")

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
    ) -> str:
        model = model or settings.ollama_llm_model
        payload: dict = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        try:
            resp = await self._http.post("/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()["response"]
        except httpx.HTTPError as e:
            raise OllamaError(f"Generation failed: {e}") from e

    async def generate_stream(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
    ) -> AsyncIterator[str]:
        model = model or settings.ollama_llm_model
        payload: dict = {"model": model, "prompt": prompt, "stream": True}
        if system:
            payload["system"] = system
        try:
            async with self._http.stream(
                "POST", "/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if token := chunk.get("response", ""):
                            yield token
                        if chunk.get("done"):
                            break
        except httpx.HTTPError as e:
            raise OllamaError(f"Stream generation failed: {e}") from e
