import time
from typing import AsyncIterator

import structlog

from src.core.schemas import QueryResponse, QueryTiming, SourceReference
from src.infrastructure.neo4j.graph_traversal import GraphTraversal
from src.infrastructure.neo4j.vector_search import VectorSearch
from src.infrastructure.ollama.client import OllamaClient
from src.services.embedding_service import EmbeddingService
from src.services.llm_service import LLMService
from src.utils.text import prepare_query_embedding

logger = structlog.get_logger()


class QueryService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_search: VectorSearch,
        graph_traversal: GraphTraversal,
        llm_service: LLMService,
        ollama: OllamaClient,
    ):
        self._embedding = embedding_service
        self._vector = vector_search
        self._graph = graph_traversal
        self._llm = llm_service
        self._ollama = ollama

    async def query(
        self,
        question: str,
        top_k: int = 10,
        include_graph_context: bool = True,
    ) -> QueryResponse:
        total_start = time.perf_counter()

        # Step 1: Embed the query
        t0 = time.perf_counter()
        query_text = prepare_query_embedding(question)
        embeddings = await self._ollama.embed([query_text])
        query_embedding = embeddings[0]
        embedding_ms = (time.perf_counter() - t0) * 1000

        # Step 2: Vector search
        t0 = time.perf_counter()
        wi_results = await self._vector.search_work_items(query_embedding, top_k=top_k)
        pr_results = await self._vector.search_pull_requests(query_embedding, top_k=top_k)
        vector_search_ms = (time.perf_counter() - t0) * 1000

        # Step 3: Graph traversal for context expansion
        t0 = time.perf_counter()
        context_parts: list[str] = []
        sources: list[SourceReference] = []

        for wi in wi_results:
            sources.append(SourceReference(
                node_type="WorkItem",
                ado_id=wi["ado_id"],
                title=wi["title"],
                relevance_score=wi["score"],
            ))

            if include_graph_context:
                ctx = await self._graph.expand_work_item(wi["ado_id"])
                if ctx:
                    context_parts.append(_format_work_item_context(wi, ctx))
                else:
                    context_parts.append(_format_basic_work_item(wi))
            else:
                context_parts.append(_format_basic_work_item(wi))

        for pr in pr_results:
            sources.append(SourceReference(
                node_type="PullRequest",
                ado_id=pr["ado_id"],
                title=pr["title"],
                relevance_score=pr["score"],
            ))

            if include_graph_context:
                ctx = await self._graph.expand_pull_request(pr["ado_id"])
                if ctx:
                    context_parts.append(_format_pr_context(pr, ctx))
                else:
                    context_parts.append(_format_basic_pr(pr))
            else:
                context_parts.append(_format_basic_pr(pr))

        graph_traversal_ms = (time.perf_counter() - t0) * 1000

        # Step 4: LLM answer generation
        t0 = time.perf_counter()
        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant data found."
        answer = await self._llm.generate_answer(question, context)
        llm_generation_ms = (time.perf_counter() - t0) * 1000

        total_ms = (time.perf_counter() - total_start) * 1000

        return QueryResponse(
            answer=answer,
            sources=sources,
            timing=QueryTiming(
                embedding_ms=embedding_ms,
                vector_search_ms=vector_search_ms,
                graph_traversal_ms=graph_traversal_ms,
                llm_generation_ms=llm_generation_ms,
                total_ms=total_ms,
            ),
        )

    async def query_stream(
        self,
        question: str,
        top_k: int = 10,
        include_graph_context: bool = True,
    ) -> AsyncIterator[str]:
        """Same as query() but streams the LLM answer."""
        query_text = prepare_query_embedding(question)
        embeddings = await self._ollama.embed([query_text])
        query_embedding = embeddings[0]

        wi_results = await self._vector.search_work_items(query_embedding, top_k=top_k)
        pr_results = await self._vector.search_pull_requests(query_embedding, top_k=top_k)

        context_parts: list[str] = []
        for wi in wi_results:
            if include_graph_context:
                ctx = await self._graph.expand_work_item(wi["ado_id"])
                if ctx:
                    context_parts.append(_format_work_item_context(wi, ctx))
                    continue
            context_parts.append(_format_basic_work_item(wi))

        for pr in pr_results:
            if include_graph_context:
                ctx = await self._graph.expand_pull_request(pr["ado_id"])
                if ctx:
                    context_parts.append(_format_pr_context(pr, ctx))
                    continue
            context_parts.append(_format_basic_pr(pr))

        context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant data found."
        async for token in self._llm.generate_answer_stream(question, context):
            yield token


def _format_basic_work_item(wi: dict) -> str:
    return (
        f"[Work Item #{wi['ado_id']}] {wi.get('work_item_type', '')} - {wi['title']}\n"
        f"State: {wi.get('state', 'N/A')}\n"
        f"Description: {wi.get('description', 'N/A')}"
    )


def _format_work_item_context(wi: dict, ctx: dict) -> str:
    lines = [
        f"[Work Item #{wi['ado_id']}] {wi.get('work_item_type', '')} - {wi['title']}",
        f"State: {wi.get('state', 'N/A')}",
    ]
    if ctx.get("assignee"):
        lines.append(f"Assigned to: {ctx['assignee']}")
    if ctx.get("creator"):
        lines.append(f"Created by: {ctx['creator']}")
    if ctx.get("iteration"):
        lines.append(f"Sprint: {ctx['iteration']}")
    if ctx.get("project"):
        lines.append(f"Project: {ctx['project']}")
    if ctx.get("parent"):
        lines.append(f"Parent: #{ctx['parent']['ado_id']} - {ctx['parent']['title']}")
    if ctx.get("children"):
        children_str = ", ".join(f"#{c['ado_id']}" for c in ctx["children"])
        lines.append(f"Children: {children_str}")
    if ctx.get("related_items"):
        related_str = ", ".join(f"#{r['ado_id']}" for r in ctx["related_items"])
        lines.append(f"Related: {related_str}")
    if ctx.get("pull_requests"):
        for pr in ctx["pull_requests"]:
            lines.append(f"PR: #{pr['ado_id']} - {pr['title']} ({pr.get('status', '')})")
    if ctx.get("reviewers"):
        lines.append(f"Reviewers: {', '.join(ctx['reviewers'])}")
    lines.append(f"Description: {wi.get('description', 'N/A')}")
    return "\n".join(lines)


def _format_basic_pr(pr: dict) -> str:
    return (
        f"[PR #{pr['ado_id']}] {pr['title']}\n"
        f"Status: {pr.get('status', 'N/A')}\n"
        f"Description: {pr.get('description', 'N/A')}"
    )


def _format_pr_context(pr: dict, ctx: dict) -> str:
    lines = [
        f"[PR #{pr['ado_id']}] {pr['title']}",
        f"Status: {pr.get('status', 'N/A')}",
    ]
    if ctx.get("author"):
        lines.append(f"Author: {ctx['author']}")
    if ctx.get("repository"):
        lines.append(f"Repository: {ctx['repository']}")
    if ctx.get("reviewers"):
        lines.append(f"Reviewers: {', '.join(ctx['reviewers'])}")
    if ctx.get("linked_work_items"):
        for wi in ctx["linked_work_items"]:
            lines.append(f"Linked: #{wi['ado_id']} ({wi.get('type', '')}) - {wi['title']}")
    lines.append(f"Description: {pr.get('description', 'N/A')}")
    return "\n".join(lines)
