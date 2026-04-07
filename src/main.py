from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.config import settings
from src.infrastructure.neo4j.driver import create_neo4j_driver, verify_neo4j_connection
from src.infrastructure.neo4j.schema import ensure_schema
from src.infrastructure.ollama.client import OllamaClient
from src.utils.logging import setup_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("starting_knowledge_rag")

    # Neo4j
    driver = await create_neo4j_driver()
    if await verify_neo4j_connection(driver):
        logger.info("neo4j_connected", uri=settings.neo4j_uri)
        await ensure_schema(driver)
    else:
        logger.warning("neo4j_unavailable", uri=settings.neo4j_uri)
    app.state.neo4j_driver = driver

    # Ollama
    ollama = OllamaClient()
    if await ollama.is_available():
        models = await ollama.list_models()
        logger.info("ollama_connected", models=models)
    else:
        logger.warning("ollama_unavailable", url=settings.ollama_base_url)
    app.state.ollama_client = ollama

    yield

    # Shutdown
    await ollama.close()
    await driver.close()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Knowledge Graph RAG",
    description="Azure DevOps → Neo4j → Hybrid Retrieval → Ollama LLM",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
from src.api.routers import graph, health, ingest, query  # noqa: E402

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)
