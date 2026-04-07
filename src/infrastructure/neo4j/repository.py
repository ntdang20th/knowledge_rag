import structlog
from neo4j import AsyncDriver

from src.core.models import PullRequest, WorkItem
from src.infrastructure.neo4j import queries

logger = structlog.get_logger()


class Neo4jRepository:
    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def upsert_work_items(self, items: list[WorkItem], project_name: str) -> None:
        if not items:
            return

        work_item_data = [
            {
                "ado_id": wi.ado_id,
                "title": wi.title,
                "description": wi.description,
                "work_item_type": wi.work_item_type,
                "state": wi.state,
                "area_path": wi.area_path,
                "tags": wi.tags,
                "priority": wi.priority,
                "story_points": wi.story_points,
                "created_date": wi.created_date.isoformat() if wi.created_date else None,
                "changed_date": wi.changed_date.isoformat() if wi.changed_date else None,
            }
            for wi in items
        ]

        async with self._driver.session() as session:
            await session.run(queries.UPSERT_WORK_ITEMS, items=work_item_data)

            # Assigned to
            assigned = [
                {
                    "ado_id": wi.ado_id,
                    "assigned_to_unique_name": wi.assigned_to.unique_name,
                    "assigned_to_display_name": wi.assigned_to.display_name,
                }
                for wi in items
                if wi.assigned_to
            ]
            if assigned:
                await session.run(queries.UPSERT_WORK_ITEM_ASSIGNED_TO, items=assigned)

            # Created by
            created = [
                {
                    "ado_id": wi.ado_id,
                    "created_by_unique_name": wi.created_by.unique_name,
                    "created_by_display_name": wi.created_by.display_name,
                }
                for wi in items
                if wi.created_by
            ]
            if created:
                await session.run(queries.UPSERT_WORK_ITEM_CREATED_BY, items=created)

            # Iteration
            iteration_items = [
                {
                    "ado_id": wi.ado_id,
                    "iteration_path": wi.iteration_path,
                    "iteration_name": wi.iteration_path.rsplit("\\", 1)[-1] if wi.iteration_path else "",
                }
                for wi in items
                if wi.iteration_path
            ]
            if iteration_items:
                await session.run(queries.UPSERT_WORK_ITEM_ITERATION, items=iteration_items)

            # Project
            project_items = [
                {
                    "ado_id": wi.ado_id,
                    "project_id": wi.project_id,
                    "project_name": project_name,
                }
                for wi in items
                if wi.project_id
            ]
            if project_items:
                await session.run(queries.UPSERT_WORK_ITEM_PROJECT, items=project_items)

            # Parent/child relationships
            parent_links = []
            related_links = []
            pr_links = []
            for wi in items:
                for rel in wi.relations:
                    if rel.relation_type == "parent":
                        parent_links.append({"child_id": wi.ado_id, "parent_id": rel.target_id})
                    elif rel.relation_type == "child":
                        parent_links.append({"child_id": rel.target_id, "parent_id": wi.ado_id})
                    elif rel.relation_type == "related":
                        related_links.append({"source_id": wi.ado_id, "target_id": rel.target_id})
                    elif rel.relation_type == "pull_request":
                        pr_links.append({"work_item_id": wi.ado_id, "pr_id": rel.target_id})

            if parent_links:
                await session.run(queries.UPSERT_WORK_ITEM_PARENT, items=parent_links)
            if related_links:
                await session.run(queries.UPSERT_WORK_ITEM_RELATED, items=related_links)
            if pr_links:
                await session.run(queries.UPSERT_WORK_ITEM_PR_LINK, items=pr_links)

        logger.info("upserted_work_items", count=len(items))

    async def upsert_pull_requests(self, prs: list[PullRequest]) -> None:
        if not prs:
            return

        pr_data = [
            {
                "ado_id": pr.ado_id,
                "title": pr.title,
                "description": pr.description,
                "status": pr.status,
                "source_branch": pr.source_branch,
                "target_branch": pr.target_branch,
                "created_date": pr.created_date.isoformat() if pr.created_date else None,
                "closed_date": pr.closed_date.isoformat() if pr.closed_date else None,
                "merge_status": pr.merge_status,
            }
            for pr in prs
        ]

        async with self._driver.session() as session:
            await session.run(queries.UPSERT_PULL_REQUESTS, items=pr_data)

            # Created by
            created = [
                {
                    "ado_id": pr.ado_id,
                    "created_by_unique_name": pr.created_by.unique_name,
                    "created_by_display_name": pr.created_by.display_name,
                }
                for pr in prs
                if pr.created_by
            ]
            if created:
                await session.run(queries.UPSERT_PR_CREATED_BY, items=created)

            # Reviewers
            reviewer_data = []
            for pr in prs:
                for rev in pr.reviewers:
                    reviewer_data.append({
                        "pr_id": pr.ado_id,
                        "reviewer_unique_name": rev.person.unique_name,
                        "reviewer_display_name": rev.person.display_name,
                        "vote": rev.vote,
                    })
            if reviewer_data:
                await session.run(queries.UPSERT_PR_REVIEWERS, items=reviewer_data)

            # Repository
            repo_items = [
                {
                    "ado_id": pr.ado_id,
                    "repo_id": pr.repository_id,
                    "repo_name": "",
                }
                for pr in prs
                if pr.repository_id
            ]
            if repo_items:
                await session.run(queries.UPSERT_PR_REPOSITORY, items=repo_items)

            # Project
            proj_items = [
                {"ado_id": pr.ado_id, "project_id": pr.project_id}
                for pr in prs
                if pr.project_id
            ]
            if proj_items:
                await session.run(queries.UPSERT_PR_PROJECT, items=proj_items)

            # Linked work items
            wi_links = []
            for pr in prs:
                for wi_id in pr.linked_work_item_ids:
                    wi_links.append({"work_item_id": wi_id, "pr_id": pr.ado_id})
            if wi_links:
                await session.run(queries.UPSERT_WORK_ITEM_PR_LINK, items=wi_links)

        logger.info("upserted_pull_requests", count=len(prs))

    async def store_embeddings(
        self, node_label: str, id_embedding_pairs: list[dict]
    ) -> None:
        if not id_embedding_pairs:
            return
        query = (
            queries.STORE_WORK_ITEM_EMBEDDINGS
            if node_label == "WorkItem"
            else queries.STORE_PR_EMBEDDINGS
        )
        async with self._driver.session() as session:
            await session.run(query, items=id_embedding_pairs)
        logger.info("stored_embeddings", label=node_label, count=len(id_embedding_pairs))

    async def get_graph_stats(self) -> dict:
        async with self._driver.session() as session:
            node_result = await session.run(queries.GRAPH_NODE_COUNTS)
            node_counts = {rec["label"]: rec["cnt"] async for rec in node_result}

            rel_result = await session.run(queries.GRAPH_RELATIONSHIP_COUNTS)
            rel_counts = {rec["rel_type"]: rec["cnt"] async for rec in rel_result}

        return {"node_counts": node_counts, "relationship_counts": rel_counts}

    async def get_sync_state(self, entity_type: str) -> str | None:
        async with self._driver.session() as session:
            result = await session.run(queries.GET_SYNC_STATE, entity_type=entity_type)
            record = await result.single()
            if record and record["last_sync_at"]:
                return str(record["last_sync_at"])
        return None

    async def update_sync_state(self, entity_type: str, last_sync_at: str) -> None:
        async with self._driver.session() as session:
            await session.run(
                queries.UPSERT_SYNC_STATE,
                entity_type=entity_type,
                last_sync_at=last_sync_at,
            )
