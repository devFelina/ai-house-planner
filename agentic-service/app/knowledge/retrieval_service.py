from __future__ import annotations

from typing import Any, Callable

from app.knowledge.embeddings import generate_embedding as default_generate_embedding
from app.knowledge.repository import PostgresKnowledgeRepository, RetrievedChunk

TOP_K_DEFAULT = 3
SIMILARITY_THRESHOLD = 0.3


def search_architecture_knowledge(
    query: str,
    top_k: int = TOP_K_DEFAULT,
    category_filter: str | None = None,
    repository: Any = None,
    generate_embedding: Callable[[str], list[float]] = default_generate_embedding
) -> list[RetrievedChunk]:
    """
    Semantic search against the knowledge base.
    Returns top-k most relevant chunks above the similarity threshold.
    """
    if repository is None:
        repository = PostgresKnowledgeRepository()

    query_embedding = generate_embedding(query)
    
    return repository.search(
        query_embedding=query_embedding,
        top_k=top_k,
        category_filter=category_filter,
        similarity_threshold=SIMILARITY_THRESHOLD
    )


def search_knowledge_as_dicts(
    query: str,
    top_k: int = TOP_K_DEFAULT,
    category_filter: str | None = None,
    repository: Any = None,
    generate_embedding: Callable[[str], list[float]] = default_generate_embedding
) -> list[dict[str, Any]]:
    """Convenience wrapper returning dicts for API serialization."""
    results = search_architecture_knowledge(
        query=query, 
        top_k=top_k, 
        category_filter=category_filter, 
        repository=repository, 
        generate_embedding=generate_embedding
    )
    return [
        {
            "title": r.title,
            "content": r.content,
            "category": r.category,
            "source": r.source,
            "relevance_score": r.similarity,
        }
        for r in results
    ]
