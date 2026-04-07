import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_query_service
from src.core.schemas import QueryRequest, QueryResponse
from src.services.query_service import QueryService

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    service: QueryService = Depends(get_query_service),
):
    return await service.query(
        question=request.question,
        top_k=request.top_k,
        include_graph_context=request.include_graph_context,
    )


@router.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    service: QueryService = Depends(get_query_service),
):
    async def event_generator():
        async for token in service.query_stream(
            question=request.question,
            top_k=request.top_k,
            include_graph_context=request.include_graph_context,
        ):
            yield {"event": "token", "data": json.dumps({"token": token})}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_generator())
