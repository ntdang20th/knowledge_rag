from datetime import datetime, timezone

import structlog

from src.infrastructure.azure_devops.client import AzureDevOpsClient
from src.infrastructure.azure_devops.mappers import map_pull_request, map_work_item
from src.infrastructure.azure_devops.pull_requests import (
    fetch_pr_reviewers,
    fetch_pr_work_items,
    fetch_pull_requests,
    fetch_repositories,
)
from src.infrastructure.azure_devops.work_items import (
    fetch_work_item_ids,
    fetch_work_items_batch,
)
from src.infrastructure.neo4j.repository import Neo4jRepository
from src.services.embedding_service import EmbeddingService

logger = structlog.get_logger()


class IngestService:
    def __init__(
        self,
        ado_client: AzureDevOpsClient,
        neo4j_repo: Neo4jRepository,
        embedding_service: EmbeddingService,
    ):
        self._ado = ado_client
        self._repo = neo4j_repo
        self._embedding = embedding_service

    async def sync_all(self, full_sync: bool = False) -> dict:
        start = datetime.now(timezone.utc)

        project_id = await self._ado.get_project_id()
        project_name = self._ado.project

        wi_count = await self._sync_work_items(project_id, project_name, full_sync)
        pr_count = await self._sync_pull_requests(project_id, full_sync)
        embed_count = await self._generate_embeddings()

        duration = (datetime.now(timezone.utc) - start).total_seconds()
        logger.info(
            "sync_completed",
            work_items=wi_count,
            pull_requests=pr_count,
            embeddings=embed_count,
            duration_seconds=duration,
        )
        return {
            "work_items_synced": wi_count,
            "pull_requests_synced": pr_count,
            "embeddings_generated": embed_count,
            "duration_seconds": duration,
        }

    async def sync_work_items(self, full_sync: bool = False) -> dict:
        start = datetime.now(timezone.utc)
        project_id = await self._ado.get_project_id()
        project_name = self._ado.project
        wi_count = await self._sync_work_items(project_id, project_name, full_sync)
        embed_count = await self._generate_embeddings()
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        return {
            "work_items_synced": wi_count,
            "pull_requests_synced": 0,
            "embeddings_generated": embed_count,
            "duration_seconds": duration,
        }

    async def sync_pull_requests(self, full_sync: bool = False) -> dict:
        start = datetime.now(timezone.utc)
        project_id = await self._ado.get_project_id()
        pr_count = await self._sync_pull_requests(project_id, full_sync)
        embed_count = await self._generate_embeddings()
        duration = (datetime.now(timezone.utc) - start).total_seconds()
        return {
            "work_items_synced": 0,
            "pull_requests_synced": pr_count,
            "embeddings_generated": embed_count,
            "duration_seconds": duration,
        }

    async def _sync_work_items(
        self, project_id: str, project_name: str, full_sync: bool
    ) -> int:
        since = None
        if not full_sync:
            since = await self._repo.get_sync_state("work_items")

        ids = await fetch_work_item_ids(self._ado, since=since)
        if not ids:
            logger.info("no_work_items_to_sync")
            return 0

        raw_items = await fetch_work_items_batch(self._ado, ids)
        items = [map_work_item(raw, project_id=project_id) for raw in raw_items]

        await self._repo.upsert_work_items(items, project_name=project_name)
        await self._repo.update_sync_state(
            "work_items", datetime.now(timezone.utc).isoformat()
        )
        return len(items)

    async def _sync_pull_requests(self, project_id: str, full_sync: bool) -> int:
        since = None
        if not full_sync:
            since = await self._repo.get_sync_state("pull_requests")

        repos = await fetch_repositories(self._ado)
        total = 0

        for repo in repos:
            repo_id = repo["id"]
            raw_prs = await fetch_pull_requests(self._ado, repo_id, since=since)

            prs = []
            for raw_pr in raw_prs:
                pr_id = raw_pr["pullRequestId"]
                reviewers = await fetch_pr_reviewers(self._ado, repo_id, pr_id)
                linked_wi_ids = await fetch_pr_work_items(self._ado, repo_id, pr_id)
                pr = map_pull_request(
                    raw_pr,
                    reviewers=reviewers,
                    linked_work_item_ids=linked_wi_ids,
                    project_id=project_id,
                )
                prs.append(pr)

            if prs:
                await self._repo.upsert_pull_requests(prs)
                total += len(prs)

        await self._repo.update_sync_state(
            "pull_requests", datetime.now(timezone.utc).isoformat()
        )
        return total

    async def _generate_embeddings(self) -> int:
        """Generate embeddings for nodes that don't have them yet."""
        # Query nodes missing embeddings
        count = 0
        for label in ("WorkItem", "PullRequest"):
            items = await self._get_items_without_embeddings(label)
            if not items:
                continue
            pairs = await self._embedding.embed_documents(items)
            await self._repo.store_embeddings(label, pairs)
            count += len(pairs)
        return count

    async def _get_items_without_embeddings(self, label: str) -> list[dict]:
        query = f"""
        MATCH (n:{label})
        WHERE n.embedding IS NULL
        RETURN n.ado_id AS ado_id, n.title AS title, n.description AS description
        """
        async with self._repo._driver.session() as session:
            result = await session.run(query)
            return [dict(record) async for record in result]
