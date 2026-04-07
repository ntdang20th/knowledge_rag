# --- Work Items ---

UPSERT_WORK_ITEMS = """
UNWIND $items AS item
MERGE (w:WorkItem {ado_id: item.ado_id})
SET w.title = item.title,
    w.description = item.description,
    w.work_item_type = item.work_item_type,
    w.state = item.state,
    w.area_path = item.area_path,
    w.tags = item.tags,
    w.priority = item.priority,
    w.story_points = item.story_points,
    w.created_date = datetime(item.created_date),
    w.changed_date = datetime(item.changed_date)
"""

UPSERT_WORK_ITEM_ASSIGNED_TO = """
UNWIND $items AS item
MATCH (w:WorkItem {ado_id: item.ado_id})
MERGE (p:Person {unique_name: item.assigned_to_unique_name})
SET p.display_name = item.assigned_to_display_name
MERGE (w)-[:ASSIGNED_TO]->(p)
"""

UPSERT_WORK_ITEM_CREATED_BY = """
UNWIND $items AS item
MATCH (w:WorkItem {ado_id: item.ado_id})
MERGE (p:Person {unique_name: item.created_by_unique_name})
SET p.display_name = item.created_by_display_name
MERGE (w)-[:CREATED_BY]->(p)
"""

UPSERT_WORK_ITEM_ITERATION = """
UNWIND $items AS item
MATCH (w:WorkItem {ado_id: item.ado_id})
MERGE (i:Iteration {path: item.iteration_path})
SET i.name = item.iteration_name
MERGE (w)-[:PART_OF_ITERATION]->(i)
"""

UPSERT_WORK_ITEM_PROJECT = """
UNWIND $items AS item
MATCH (w:WorkItem {ado_id: item.ado_id})
MERGE (pj:Project {ado_id: item.project_id})
SET pj.name = item.project_name
MERGE (w)-[:BELONGS_TO_PROJECT]->(pj)
"""

UPSERT_WORK_ITEM_PARENT = """
UNWIND $items AS item
MATCH (child:WorkItem {ado_id: item.child_id})
MATCH (parent:WorkItem {ado_id: item.parent_id})
MERGE (parent)-[:PARENT_OF]->(child)
"""

UPSERT_WORK_ITEM_RELATED = """
UNWIND $items AS item
MATCH (w1:WorkItem {ado_id: item.source_id})
MATCH (w2:WorkItem {ado_id: item.target_id})
MERGE (w1)-[:RELATED_TO]->(w2)
"""

UPSERT_WORK_ITEM_PR_LINK = """
UNWIND $items AS item
MATCH (w:WorkItem {ado_id: item.work_item_id})
MERGE (pr:PullRequest {ado_id: item.pr_id})
MERGE (w)-[:LINKED_TO_PR]->(pr)
"""

# --- Pull Requests ---

UPSERT_PULL_REQUESTS = """
UNWIND $items AS item
MERGE (pr:PullRequest {ado_id: item.ado_id})
SET pr.title = item.title,
    pr.description = item.description,
    pr.status = item.status,
    pr.source_branch = item.source_branch,
    pr.target_branch = item.target_branch,
    pr.created_date = datetime(item.created_date),
    pr.closed_date = CASE WHEN item.closed_date IS NOT NULL THEN datetime(item.closed_date) ELSE NULL END,
    pr.merge_status = item.merge_status
"""

UPSERT_PR_CREATED_BY = """
UNWIND $items AS item
MATCH (pr:PullRequest {ado_id: item.ado_id})
MERGE (p:Person {unique_name: item.created_by_unique_name})
SET p.display_name = item.created_by_display_name
MERGE (pr)-[:CREATED_BY]->(p)
"""

UPSERT_PR_REVIEWERS = """
UNWIND $items AS item
MATCH (pr:PullRequest {ado_id: item.pr_id})
MERGE (p:Person {unique_name: item.reviewer_unique_name})
SET p.display_name = item.reviewer_display_name
MERGE (pr)-[r:REVIEWED_BY]->(p)
SET r.vote = item.vote
"""

UPSERT_PR_REPOSITORY = """
UNWIND $items AS item
MATCH (pr:PullRequest {ado_id: item.ado_id})
MERGE (r:Repository {ado_id: item.repo_id})
SET r.name = item.repo_name
MERGE (pr)-[:TARGETS_REPO]->(r)
"""

UPSERT_PR_PROJECT = """
UNWIND $items AS item
MATCH (pr:PullRequest {ado_id: item.ado_id})
MERGE (pj:Project {ado_id: item.project_id})
MERGE (pr)-[:BELONGS_TO_PROJECT]->(pj)
"""

# --- Embeddings ---

STORE_WORK_ITEM_EMBEDDINGS = """
UNWIND $items AS item
MATCH (w:WorkItem {ado_id: item.ado_id})
SET w.embedding = item.embedding
"""

STORE_PR_EMBEDDINGS = """
UNWIND $items AS item
MATCH (pr:PullRequest {ado_id: item.ado_id})
SET pr.embedding = item.embedding
"""

# --- Vector Search ---

VECTOR_SEARCH_WORK_ITEMS = """
CALL db.index.vector.queryNodes('work_item_embedding', $top_k, $query_embedding)
YIELD node, score
RETURN node.ado_id AS ado_id, node.title AS title, node.description AS description,
       node.work_item_type AS work_item_type, node.state AS state, score
ORDER BY score DESC
"""

VECTOR_SEARCH_PULL_REQUESTS = """
CALL db.index.vector.queryNodes('pull_request_embedding', $top_k, $query_embedding)
YIELD node, score
RETURN node.ado_id AS ado_id, node.title AS title, node.description AS description,
       node.status AS status, score
ORDER BY score DESC
"""

# --- Graph Traversal ---

EXPAND_WORK_ITEM_CONTEXT = """
MATCH (w:WorkItem {ado_id: $ado_id})
OPTIONAL MATCH (w)-[:ASSIGNED_TO]->(assignee:Person)
OPTIONAL MATCH (w)-[:CREATED_BY]->(creator:Person)
OPTIONAL MATCH (w)-[:PART_OF_ITERATION]->(iter:Iteration)
OPTIONAL MATCH (w)-[:BELONGS_TO_PROJECT]->(proj:Project)
OPTIONAL MATCH (parent:WorkItem)-[:PARENT_OF]->(w)
OPTIONAL MATCH (w)-[:PARENT_OF]->(child:WorkItem)
OPTIONAL MATCH (w)-[:RELATED_TO]-(related:WorkItem)
OPTIONAL MATCH (w)-[:LINKED_TO_PR]->(pr:PullRequest)
OPTIONAL MATCH (pr)-[:REVIEWED_BY]->(reviewer:Person)
RETURN w, assignee, creator, iter, proj, parent,
       collect(DISTINCT child) AS children,
       collect(DISTINCT related) AS related_items,
       collect(DISTINCT pr) AS pull_requests,
       collect(DISTINCT reviewer) AS reviewers
"""

EXPAND_PR_CONTEXT = """
MATCH (pr:PullRequest {ado_id: $ado_id})
OPTIONAL MATCH (pr)-[:CREATED_BY]->(author:Person)
OPTIONAL MATCH (pr)-[:REVIEWED_BY]->(reviewer:Person)
OPTIONAL MATCH (pr)-[:TARGETS_REPO]->(repo:Repository)
OPTIONAL MATCH (pr)-[:BELONGS_TO_PROJECT]->(proj:Project)
OPTIONAL MATCH (wi:WorkItem)-[:LINKED_TO_PR]->(pr)
RETURN pr, author, repo, proj,
       collect(DISTINCT {reviewer: reviewer.display_name, unique_name: reviewer.unique_name}) AS reviewers,
       collect(DISTINCT wi) AS linked_work_items
"""

# --- Graph Stats ---

GRAPH_NODE_COUNTS = """
CALL {
    MATCH (w:WorkItem) RETURN 'WorkItem' AS label, count(w) AS cnt
    UNION ALL
    MATCH (pr:PullRequest) RETURN 'PullRequest' AS label, count(pr) AS cnt
    UNION ALL
    MATCH (p:Person) RETURN 'Person' AS label, count(p) AS cnt
    UNION ALL
    MATCH (r:Repository) RETURN 'Repository' AS label, count(r) AS cnt
    UNION ALL
    MATCH (i:Iteration) RETURN 'Iteration' AS label, count(i) AS cnt
    UNION ALL
    MATCH (pj:Project) RETURN 'Project' AS label, count(pj) AS cnt
}
RETURN label, cnt
"""

GRAPH_RELATIONSHIP_COUNTS = """
CALL {
    MATCH ()-[r:ASSIGNED_TO]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:CREATED_BY]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:PART_OF_ITERATION]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:BELONGS_TO_PROJECT]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:PARENT_OF]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:RELATED_TO]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:LINKED_TO_PR]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:REVIEWED_BY]->() RETURN type(r) AS rel_type, count(r) AS cnt
    UNION ALL
    MATCH ()-[r:TARGETS_REPO]->() RETURN type(r) AS rel_type, count(r) AS cnt
}
RETURN rel_type, cnt
"""

# --- Sync State ---

GET_SYNC_STATE = """
MATCH (s:SyncState {entity_type: $entity_type})
RETURN s.last_sync_at AS last_sync_at
"""

UPSERT_SYNC_STATE = """
MERGE (s:SyncState {entity_type: $entity_type})
SET s.last_sync_at = datetime($last_sync_at)
"""
