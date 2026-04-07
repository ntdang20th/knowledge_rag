from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import get_graph_traversal, get_neo4j_repository
from src.core.schemas import GraphStatsResponse
from src.infrastructure.neo4j.graph_traversal import GraphTraversal
from src.infrastructure.neo4j.repository import Neo4jRepository

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/stats", response_model=GraphStatsResponse)
async def graph_stats(
    repo: Neo4jRepository = Depends(get_neo4j_repository),
):
    stats = await repo.get_graph_stats()
    return GraphStatsResponse(**stats)


@router.get("/work-item/{ado_id}")
async def get_work_item_context(
    ado_id: int,
    traversal: GraphTraversal = Depends(get_graph_traversal),
):
    result = await traversal.expand_work_item(ado_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Work item #{ado_id} not found")
    return result


@router.get("/pull-request/{ado_id}")
async def get_pull_request_context(
    ado_id: int,
    traversal: GraphTraversal = Depends(get_graph_traversal),
):
    result = await traversal.expand_pull_request(ado_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"PR #{ado_id} not found")
    return result
