from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure DevOps
    azure_devops_org_url: str = "https://dev.azure.com/your-org"
    azure_devops_project: str = "your-project"
    azure_devops_pat: str = ""

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen2.5-coder:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"

    # RAG Settings
    embedding_dimensions: int = 768
    vector_search_top_k: int = 10
    graph_traversal_depth: int = 2

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
