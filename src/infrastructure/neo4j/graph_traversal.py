from neo4j import AsyncDriver

from src.infrastructure.neo4j import queries


class GraphTraversal:
    def __init__(self, driver: AsyncDriver):
        self._driver = driver

    async def expand_work_item(self, ado_id: int) -> dict | None:
        async with self._driver.session() as session:
            result = await session.run(queries.EXPAND_WORK_ITEM_CONTEXT, ado_id=ado_id)
            record = await result.single()
            if not record:
                return None

            w = record["w"]
            return {
                "work_item": dict(w) if w else None,
                "assignee": record["assignee"]["display_name"] if record["assignee"] else None,
                "creator": record["creator"]["display_name"] if record["creator"] else None,
                "iteration": record["iter"]["path"] if record["iter"] else None,
                "project": record["proj"]["name"] if record["proj"] else None,
                "parent": {
                    "ado_id": record["parent"]["ado_id"],
                    "title": record["parent"]["title"],
                } if record["parent"] else None,
                "children": [
                    {"ado_id": c["ado_id"], "title": c["title"]}
                    for c in record["children"]
                ],
                "related_items": [
                    {"ado_id": r["ado_id"], "title": r["title"]}
                    for r in record["related_items"]
                ],
                "pull_requests": [
                    {"ado_id": pr["ado_id"], "title": pr["title"], "status": pr["status"]}
                    for pr in record["pull_requests"]
                ],
                "reviewers": [
                    r["display_name"] for r in record["reviewers"]
                ],
            }

    async def expand_pull_request(self, ado_id: int) -> dict | None:
        async with self._driver.session() as session:
            result = await session.run(queries.EXPAND_PR_CONTEXT, ado_id=ado_id)
            record = await result.single()
            if not record:
                return None

            pr = record["pr"]
            return {
                "pull_request": dict(pr) if pr else None,
                "author": record["author"]["display_name"] if record["author"] else None,
                "repository": record["repo"]["name"] if record["repo"] else None,
                "project": record["proj"]["name"] if record["proj"] else None,
                "reviewers": [
                    r["reviewer"] for r in record["reviewers"] if r["reviewer"]
                ],
                "linked_work_items": [
                    {"ado_id": wi["ado_id"], "title": wi["title"], "type": wi["work_item_type"]}
                    for wi in record["linked_work_items"]
                ],
            }
