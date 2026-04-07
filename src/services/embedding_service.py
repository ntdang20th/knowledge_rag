import structlog

from src.infrastructure.ollama.client import OllamaClient
from src.utils.text import prepare_document_embedding

logger = structlog.get_logger()

BATCH_SIZE = 50


class EmbeddingService:
    def __init__(self, ollama: OllamaClient):
        self._ollama = ollama

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            embeddings = await self._ollama.embed(batch)
            all_embeddings.extend(embeddings)
            logger.info("embedded_batch", offset=i, batch_size=len(batch))
        return all_embeddings

    async def embed_documents(
        self, items: list[dict],
    ) -> list[dict]:
        """Embed a list of items with title+description, return id-embedding pairs.

        Each item must have keys: ado_id, title, description.
        """
        if not items:
            return []

        texts = [
            prepare_document_embedding(item["title"], item.get("description", ""))
            for item in items
        ]
        embeddings = await self.embed_texts(texts)

        return [
            {"ado_id": item["ado_id"], "embedding": emb}
            for item, emb in zip(items, embeddings)
        ]
