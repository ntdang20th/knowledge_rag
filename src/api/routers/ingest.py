from fastapi import APIRouter, BackgroundTasks, Depends

from src.api.dependencies import get_ingest_service
from src.core.schemas import IngestRequest, IngestResponse
from src.services.ingest_service import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/sync", response_model=IngestResponse)
async def sync_all(
    request: IngestRequest = IngestRequest(),
    service: IngestService = Depends(get_ingest_service),
):
    result = await service.sync_all(full_sync=request.full_sync)
    return IngestResponse(**result)


@router.post("/work-items", response_model=IngestResponse)
async def sync_work_items(
    request: IngestRequest = IngestRequest(),
    service: IngestService = Depends(get_ingest_service),
):
    result = await service.sync_work_items(full_sync=request.full_sync)
    return IngestResponse(**result)


@router.post("/pull-requests", response_model=IngestResponse)
async def sync_pull_requests(
    request: IngestRequest = IngestRequest(),
    service: IngestService = Depends(get_ingest_service),
):
    result = await service.sync_pull_requests(full_sync=request.full_sync)
    return IngestResponse(**result)
