from fastapi import APIRouter, Depends

from src.api.dependencies import get_neo4j_repository, get_ollama_client
from src.core.schemas import HealthResponse
from src.infrastructure.neo4j.driver import verify_neo4j_connection
from src.infrastructure.neo4j.repository import Neo4jRepository
from src.infrastructure.ollama.client import OllamaClient

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    repo: Neo4jRepository = Depends(get_neo4j_repository),
    ollama: OllamaClient = Depends(get_ollama_client),
):
    neo4j_ok = await verify_neo4j_connection(repo._driver)

    ollama_ok = await ollama.is_available()
    models: list[str] = []
    if ollama_ok:
        try:
            models = await ollama.list_models()
        except Exception:
            pass

    graph_stats = {}
    if neo4j_ok:
        try:
            graph_stats = await repo.get_graph_stats()
        except Exception:
            pass

    status = "healthy" if (neo4j_ok and ollama_ok) else "degraded"

    return HealthResponse(
        status=status,
        neo4j_connected=neo4j_ok,
        ollama_available=ollama_ok,
        models_loaded=models,
        graph_stats=graph_stats,
    )
