from neo4j import AsyncDriver

from src.infrastructure.neo4j import queries


class VectorSearch:
    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def search_work_items(
        self, query_embedding: list[float], top_k: int = 10
    ) -> list[dict]:
        async with self._driver.session() as session:
            result = await session.run(
                queries.VECTOR_SEARCH_WORK_ITEMS,
                top_k=top_k,
                query_embedding=query_embedding,
            )
            return [dict(record) async for record in result]

    async def search_pull_requests(
        self, query_embedding: list[float], top_k: int = 10
    ) -> list[dict]:
        async with self._driver.session() as session:
            result = await session.run(
                queries.VECTOR_SEARCH_PULL_REQUESTS,
                top_k=top_k,
                query_embedding=query_embedding,
            )
            return [dict(record) async for record in result]
