"""Standalone script to initialize Neo4j schema (run once)."""

import asyncio

from src.infrastructure.neo4j.driver import create_neo4j_driver
from src.infrastructure.neo4j.schema import ensure_schema
from src.utils.logging import setup_logging


async def main():
    setup_logging()
    driver = await create_neo4j_driver()
    try:
        await ensure_schema(driver)
        print("Schema created successfully!")
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
