from datetime import datetime

from src.core.models import (
    Person,
    PullRequest,
    PullRequestReviewer,
    WorkItem,
    WorkItemRelation,
)
from src.utils.text import strip_html


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _parse_person(data: dict | None) -> Person | None:
    if not data:
        return None
    return Person(
        unique_name=data.get("uniqueName", data.get("id", "")),
        display_name=data.get("displayName", ""),
    )


def _parse_relations(relations: list[dict] | None) -> list[WorkItemRelation]:
    if not relations:
        return []
    result = []
    for rel in relations:
        rel_type_raw = rel.get("rel", "")
        url = rel.get("url", "")

        if rel_type_raw == "System.LinkTypes.Hierarchy-Reverse":
            # Parent link — extract ID from URL
            target_id = _extract_id_from_url(url)
            if target_id:
                result.append(WorkItemRelation(relation_type="parent", target_id=target_id))
        elif rel_type_raw == "System.LinkTypes.Hierarchy-Forward":
            target_id = _extract_id_from_url(url)
            if target_id:
                result.append(WorkItemRelation(relation_type="child", target_id=target_id))
        elif rel_type_raw == "System.LinkTypes.Related":
            target_id = _extract_id_from_url(url)
            if target_id:
                result.append(WorkItemRelation(relation_type="related", target_id=target_id))
        elif "vstfs:///Git/PullRequestId" in url:
            pr_id = _extract_pr_id_from_artifact(url)
            if pr_id:
                result.append(WorkItemRelation(relation_type="pull_request", target_id=pr_id))
    return result


def _extract_id_from_url(url: str) -> int | None:
    """Extract work item ID from Azure DevOps API URL."""
    try:
        parts = url.rstrip("/").split("/")
        return int(parts[-1])
    except (ValueError, IndexError):
        return None


def _extract_pr_id_from_artifact(url: str) -> int | None:
    """Extract PR ID from an artifact link like vstfs:///Git/PullRequestId/..."""
    try:
        parts = url.split("/")
        return int(parts[-1])
    except (ValueError, IndexError):
        return None


def map_work_item(raw: dict, project_id: str = "") -> WorkItem:
    fields = raw.get("fields", {})
    tags_raw = fields.get("System.Tags", "")
    tags = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []

    return WorkItem(
        ado_id=raw["id"],
        title=fields.get("System.Title", ""),
        description=strip_html(fields.get("System.Description", "")),
        work_item_type=fields.get("System.WorkItemType", ""),
        state=fields.get("System.State", ""),
        area_path=fields.get("System.AreaPath", ""),
        iteration_path=fields.get("System.IterationPath", ""),
        tags=tags,
        priority=fields.get("Microsoft.VSTS.Common.Priority", 0),
        story_points=fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
        assigned_to=_parse_person(fields.get("System.AssignedTo")),
        created_by=_parse_person(fields.get("System.CreatedBy")),
        created_date=_parse_datetime(fields.get("System.CreatedDate")),
        changed_date=_parse_datetime(fields.get("System.ChangedDate")),
        relations=_parse_relations(raw.get("relations")),
        project_id=project_id,
    )


def map_pull_request(
    raw: dict,
    reviewers: list[dict] | None = None,
    linked_work_item_ids: list[int] | None = None,
    project_id: str = "",
) -> PullRequest:
    reviewer_models = []
    for rev in (reviewers or raw.get("reviewers", [])):
        person = _parse_person(rev)
        if person:
            reviewer_models.append(
                PullRequestReviewer(person=person, vote=rev.get("vote", 0))
            )

    return PullRequest(
        ado_id=raw["pullRequestId"],
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        status=raw.get("status", ""),
        source_branch=raw.get("sourceRefName", ""),
        target_branch=raw.get("targetRefName", ""),
        created_date=_parse_datetime(raw.get("creationDate")),
        closed_date=_parse_datetime(raw.get("closedDate")),
        merge_status=raw.get("mergeStatus", ""),
        created_by=_parse_person(raw.get("createdBy")),
        reviewers=reviewer_models,
        repository_id=raw.get("repository", {}).get("id", ""),
        project_id=project_id,
        linked_work_item_ids=linked_work_item_ids or [],
    )
