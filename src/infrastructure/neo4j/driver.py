from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config import settings


async def create_neo4j_driver() -> AsyncDriver:
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


async def verify_neo4j_connection(driver: AsyncDriver) -> bool:
    try:
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            record = await result.single()
            return record is not None and record["n"] == 1
    except Exception:
        return False
