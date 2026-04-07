import structlog

from src.infrastructure.azure_devops.client import AzureDevOpsClient

logger = structlog.get_logger()

BATCH_SIZE = 200  # Azure DevOps API max per request


async def fetch_work_item_ids(
    client: AzureDevOpsClient,
    since: str | None = None,
) -> list[int]:
    """Fetch work item IDs using WIQL, optionally filtering by changed date."""
    where_clause = f"WHERE [System.TeamProject] = '{client.project}'"
    if since:
        where_clause += f" AND [System.ChangedDate] > '{since}'"

    wiql = f"SELECT [System.Id] FROM WorkItems {where_clause} ORDER BY [System.ChangedDate] DESC"

    data = await client.post(
        f"/{client.project}/_apis/wit/wiql",
        json={"query": wiql},
    )

    ids = [item["id"] for item in data.get("workItems", [])]
    logger.info("fetched_work_item_ids", count=len(ids), since=since)
    return ids


async def fetch_work_items_batch(
    client: AzureDevOpsClient,
    ids: list[int],
) -> list[dict]:
    """Fetch full work item details in batches of 200."""
    all_items: list[dict] = []

    for i in range(0, len(ids), BATCH_SIZE):
        batch_ids = ids[i : i + BATCH_SIZE]
        ids_str = ",".join(str(id_) for id_ in batch_ids)

        data = await client.get(
            f"/{client.project}/_apis/wit/workitems",
            params={
                "ids": ids_str,
                "$expand": "relations",
            },
        )
        items = data.get("value", [])
        all_items.extend(items)
        logger.info("fetched_work_items_batch", offset=i, batch_size=len(items))

    return all_items
