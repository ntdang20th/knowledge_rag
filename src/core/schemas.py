from pydantic import BaseModel


# --- Query ---

class QueryRequest(BaseModel):
    question: str
    top_k: int = 10
    include_graph_context: bool = True


class SourceReference(BaseModel):
    node_type: str  # "WorkItem" or "PullRequest"
    ado_id: int
    title: str
    relevance_score: float


class QueryTiming(BaseModel):
    embedding_ms: float
    vector_search_ms: float
    graph_traversal_ms: float
    llm_generation_ms: float
    total_ms: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
    timing: QueryTiming


# --- Ingest ---

class IngestRequest(BaseModel):
    full_sync: bool = False


class IngestResponse(BaseModel):
    work_items_synced: int
    pull_requests_synced: int
    embeddings_generated: int
    duration_seconds: float


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    ollama_available: bool
    models_loaded: list[str]
    graph_stats: dict


# --- Graph ---

class GraphStatsResponse(BaseModel):
    node_counts: dict[str, int]
    relationship_counts: dict[str, int]
