class KnowledgeRagError(Exception):
    """Base exception for the knowledge-rag system."""


class AzureDevOpsError(KnowledgeRagError):
    """Azure DevOps API failures."""


class Neo4jConnectionError(KnowledgeRagError):
    """Neo4j connection or query failures."""


class OllamaError(KnowledgeRagError):
    """Ollama service failures (model not loaded, timeout, etc.)."""


class EmbeddingError(KnowledgeRagError):
    """Embedding generation failures."""
