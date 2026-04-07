from bs4 import BeautifulSoup


def strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def truncate_for_embedding(text: str, max_chars: int = 24000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def prepare_embedding_text(title: str, description: str) -> str:
    desc = strip_html(description)
    text = f"{title}. {desc}".strip() if desc else title.strip()
    return truncate_for_embedding(text)


def prepare_document_embedding(title: str, description: str) -> str:
    """Prepare text for indexing with nomic-embed-text document prefix."""
    text = prepare_embedding_text(title, description)
    return f"search_document: {text}"


def prepare_query_embedding(query: str) -> str:
    """Prepare text for querying with nomic-embed-text query prefix."""
    return f"search_query: {query}"
