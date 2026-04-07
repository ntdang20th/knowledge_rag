from fastapi import Request
from neo4j import AsyncDriver

from src.infrastructure.neo4j.graph_traversal import GraphTraversal
from src.infrastructure.neo4j.repository import Neo4jRepository
from src.infrastructure.neo4j.vector_search import VectorSearch
from src.infrastructure.ollama.client import OllamaClient
from src.infrastructure.azure_devops.client import AzureDevOpsClient
from src.services.embedding_service import EmbeddingService
from src.services.ingest_service import IngestService
from src.services.llm_service import LLMService
from src.services.query_service import QueryService


def get_neo4j_driver(request: Request) -> AsyncDriver:
    return request.app.state.neo4j_driver


def get_ollama_client(request: Request) -> OllamaClient:
    return request.app.state.ollama_client


def get_neo4j_repository(request: Request) -> Neo4jRepository:
    return Neo4jRepository(get_neo4j_driver(request))


def get_vector_search(request: Request) -> VectorSearch:
    return VectorSearch(get_neo4j_driver(request))


def get_graph_traversal(request: Request) -> GraphTraversal:
    return GraphTraversal(get_neo4j_driver(request))


def get_embedding_service(request: Request) -> EmbeddingService:
    return EmbeddingService(get_ollama_client(request))


def get_llm_service(request: Request) -> LLMService:
    return LLMService(get_ollama_client(request))


def get_query_service(request: Request) -> QueryService:
    ollama = get_ollama_client(request)
    return QueryService(
        embedding_service=get_embedding_service(request),
        vector_search=get_vector_search(request),
        graph_traversal=get_graph_traversal(request),
        llm_service=get_llm_service(request),
        ollama=ollama,
    )


def get_ingest_service(request: Request) -> IngestService:
    return IngestService(
        ado_client=AzureDevOpsClient(),
        neo4j_repo=get_neo4j_repository(request),
        embedding_service=get_embedding_service(request),
    )
