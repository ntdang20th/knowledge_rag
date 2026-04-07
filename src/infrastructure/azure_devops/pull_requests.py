import structlog

from src.infrastructure.azure_devops.client import AzureDevOpsClient

logger = structlog.get_logger()

PAGE_SIZE = 100


async def fetch_repositories(client: AzureDevOpsClient) -> list[dict]:
    """Fetch all git repositories in the project."""
    data = await client.get(f"/{client.project}/_apis/git/repositories")
    return data.get("value", [])


async def fetch_pull_requests(
    client: AzureDevOpsClient,
    repository_id: str,
    since: str | None = None,
) -> list[dict]:
    """Fetch all pull requests for a repository, with pagination."""
    all_prs: list[dict] = []
    skip = 0

    while True:
        params: dict = {
            "searchCriteria.status": "all",
            "$top": str(PAGE_SIZE),
            "$skip": str(skip),
        }
        if since:
            params["searchCriteria.minTime"] = since

        data = await client.get(
            f"/{client.project}/_apis/git/repositories/{repository_id}/pullrequests",
            params=params,
        )
        prs = data.get("value", [])
        if not prs:
            break

        all_prs.extend(prs)
        skip += PAGE_SIZE

        if len(prs) < PAGE_SIZE:
            break

    logger.info("fetched_pull_requests", repo_id=repository_id, count=len(all_prs))
    return all_prs


async def fetch_pr_reviewers(
    client: AzureDevOpsClient,
    repository_id: str,
    pr_id: int,
) -> list[dict]:
    """Fetch reviewers for a specific pull request."""
    data = await client.get(
        f"/{client.project}/_apis/git/repositories/{repository_id}/pullrequests/{pr_id}/reviewers",
    )
    return data.get("value", [])


async def fetch_pr_work_items(
    client: AzureDevOpsClient,
    repository_id: str,
    pr_id: int,
) -> list[int]:
    """Fetch linked work item IDs for a pull request."""
    data = await client.get(
        f"/{client.project}/_apis/git/repositories/{repository_id}/pullrequests/{pr_id}/workitems",
    )
    return [item["id"] for item in data.get("value", []) if "id" in item]
