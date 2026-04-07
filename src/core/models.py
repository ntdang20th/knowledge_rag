from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Person:
    unique_name: str
    display_name: str = ""


@dataclass
class Project:
    ado_id: str
    name: str


@dataclass
class Repository:
    ado_id: str
    name: str
    default_branch: str = "refs/heads/main"


@dataclass
class Iteration:
    path: str
    name: str
    start_date: datetime | None = None
    finish_date: datetime | None = None


@dataclass
class WorkItemRelation:
    relation_type: str  # "parent", "child", "related", "pull_request"
    target_id: int | str


@dataclass
class WorkItem:
    ado_id: int
    title: str
    description: str = ""
    work_item_type: str = ""  # "User Story", "Bug", "Task", "Feature", "Epic"
    state: str = ""
    area_path: str = ""
    iteration_path: str = ""
    tags: list[str] = field(default_factory=list)
    priority: int = 0
    story_points: float | None = None
    assigned_to: Person | None = None
    created_by: Person | None = None
    created_date: datetime | None = None
    changed_date: datetime | None = None
    relations: list[WorkItemRelation] = field(default_factory=list)
    project_id: str = ""


@dataclass
class PullRequest:
    ado_id: int
    title: str
    description: str = ""
    status: str = ""  # "active", "completed", "abandoned"
    source_branch: str = ""
    target_branch: str = ""
    created_date: datetime | None = None
    closed_date: datetime | None = None
    merge_status: str = ""
    created_by: Person | None = None
    reviewers: list[PullRequestReviewer] = field(default_factory=list)
    repository_id: str = ""
    project_id: str = ""
    linked_work_item_ids: list[int] = field(default_factory=list)


@dataclass
class PullRequestReviewer:
    person: Person
    vote: int = 0  # 10=approved, 5=approved with suggestions, -5=wait, -10=rejected
