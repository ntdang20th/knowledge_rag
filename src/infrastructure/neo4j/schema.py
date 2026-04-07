import structlog
from neo4j import AsyncDriver

from src.config import settings

logger = structlog.get_logger()

CONSTRAINTS = [
    "CREATE CONSTRAINT work_item_ado_id IF NOT EXISTS FOR (w:WorkItem) REQUIRE w.ado_id IS UNIQUE",
    "CREATE CONSTRAINT pull_request_ado_id IF NOT EXISTS FOR (pr:PullRequest) REQUIRE pr.ado_id IS UNIQUE",
    "CREATE CONSTRAINT person_unique_name IF NOT EXISTS FOR (p:Person) REQUIRE p.unique_name IS UNIQUE",
    "CREATE CONSTRAINT repository_ado_id IF NOT EXISTS FOR (r:Repository) REQUIRE r.ado_id IS UNIQUE",
    "CREATE CONSTRAINT iteration_path IF NOT EXISTS FOR (i:Iteration) REQUIRE i.path IS UNIQUE",
    "CREATE CONSTRAINT project_ado_id IF NOT EXISTS FOR (pj:Project) REQUIRE pj.ado_id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX work_item_type_state IF NOT EXISTS FOR (w:WorkItem) ON (w.work_item_type, w.state)",
    "CREATE FULLTEXT INDEX work_item_fulltext IF NOT EXISTS FOR (w:WorkItem) ON EACH [w.title, w.description]",
    "CREATE FULLTEXT INDEX pull_request_fulltext IF NOT EXISTS FOR (pr:PullRequest) ON EACH [pr.title, pr.description]",
]

VECTOR_INDEXES = [
    f"""CREATE VECTOR INDEX work_item_embedding IF NOT EXISTS
    FOR (w:WorkItem) ON (w.embedding)
    OPTIONS {{indexConfig: {{
        `vector.dimensions`: {settings.embedding_dimensions},
        `vector.similarity_function`: 'cosine'
    }}}}""",
    f"""CREATE VECTOR INDEX pull_request_embedding IF NOT EXISTS
    FOR (pr:PullRequest) ON (pr.embedding)
    OPTIONS {{indexConfig: {{
        `vector.dimensions`: {settings.embedding_dimensions},
        `vector.similarity_function`: 'cosine'
    }}}}""",
]


async def ensure_schema(driver: AsyncDriver) -> None:
    """Create all constraints, indexes, and vector indexes idempotently."""
    async with driver.session() as session:
        for stmt in CONSTRAINTS:
            await session.run(stmt)
        logger.info("neo4j_constraints_created", count=len(CONSTRAINTS))

        for stmt in INDEXES:
            await session.run(stmt)
        logger.info("neo4j_indexes_created", count=len(INDEXES))

        for stmt in VECTOR_INDEXES:
            await session.run(stmt)
        logger.info("neo4j_vector_indexes_created", count=len(VECTOR_INDEXES))
