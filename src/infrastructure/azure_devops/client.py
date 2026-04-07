import base64

import httpx
import structlog

from src.config import settings
from src.core.exceptions import AzureDevOpsError

logger = structlog.get_logger()

API_VERSION = "7.1"


class AzureDevOpsClient:
    def __init__(
        self,
        org_url: str | None = None,
        project: str | None = None,
        pat: str | None = None,
    ):
        self._org_url = (org_url or settings.azure_devops_org_url).rstrip("/")
        self._project = project or settings.azure_devops_project
        self._pat = pat or settings.azure_devops_pat

        token = base64.b64encode(f":{self._pat}".encode()).decode()
        self._http = httpx.AsyncClient(
            base_url=self._org_url,
            headers={"Authorization": f"Basic {token}"},
            timeout=60.0,
        )

    async def close(self) -> None:
        await self._http.aclose()

    @property
    def project(self) -> str:
        return self._project

    async def get(self, path: str, params: dict | None = None) -> dict:
        params = params or {}
        params.setdefault("api-version", API_VERSION)
        try:
            resp = await self._http.get(path, params=params)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "10")
                raise AzureDevOpsError(f"Rate limited, retry after {retry_after}s")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise AzureDevOpsError(f"API error {e.response.status_code}: {e}") from e
        except httpx.HTTPError as e:
            raise AzureDevOpsError(f"HTTP error: {e}") from e

    async def post(self, path: str, json: dict, params: dict | None = None) -> dict:
        params = params or {}
        params.setdefault("api-version", API_VERSION)
        try:
            resp = await self._http.post(path, json=json, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise AzureDevOpsError(f"API error {e.response.status_code}: {e}") from e
        except httpx.HTTPError as e:
            raise AzureDevOpsError(f"HTTP error: {e}") from e

    async def get_project_id(self) -> str:
        data = await self.get(f"/_apis/projects/{self._project}")
        return data["id"]
