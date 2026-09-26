from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

from app.knowledge.embeddings import generate_embeddings_batch as default_generate_embeddings_batch
from app.knowledge.repository import PostgresKnowledgeRepository, Chunk

CHUNK_MAX_CHARS = 800
CHUNK_OVERLAP_CHARS = 100


def _chunk_document(doc: dict[str, str]) -> list[Chunk]:
    """Split a document into overlapping chunks."""
    title = doc["title"]
    content = doc["content"]
    category = doc["category"]
    source = doc.get("source", "HomePlannerAI Knowledge Base")

    # If content is small enough, return as a single chunk
    if len(content) <= CHUNK_MAX_CHARS:
        h = hashlib.sha256(f"{title}:{content}".encode()).hexdigest()[:16]
        return [Chunk(title=title, content=content, category=category, source=source, content_hash=h)]

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', content)
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > CHUNK_MAX_CHARS and current:
            h = hashlib.sha256(f"{title}:{current}".encode()).hexdigest()[:16]
            chunks.append(Chunk(title=title, content=current.strip(), category=category, source=source, content_hash=h))
            # Overlap: keep last portion
            words = current.split()
            overlap_words = words[-max(1, len(words) // 4):]
            current = " ".join(overlap_words) + " " + sentence
        else:
            current = (current + " " + sentence).strip()

    if current.strip():
        h = hashlib.sha256(f"{title}:{current}".encode()).hexdigest()[:16]
        chunks.append(Chunk(title=title, content=current.strip(), category=category, source=source, content_hash=h))

    return chunks


def seed_knowledge_base(
    repository: Any = None,
    generate_embeddings_batch: Callable[[list[str]], list[list[float]]] = default_generate_embeddings_batch
) -> tuple[int, int]:
    """Full pipeline: load seed docs → chunk → embed → store."""
    from app.knowledge.seed_documents import KNOWLEDGE_DOCUMENTS

    if repository is None:
        repository = PostgresKnowledgeRepository()

    print("[RAG] Ensuring database schema...")
    repository.ensure_schema()

    print(f"[RAG] Processing {len(KNOWLEDGE_DOCUMENTS)} documents...")
    all_chunks: list[Chunk] = []
    for doc in KNOWLEDGE_DOCUMENTS:
        all_chunks.extend(_chunk_document(doc))

    print(f"[RAG] Created {len(all_chunks)} chunks. Generating embeddings...")
    texts = [f"{c.title}: {c.content}" for c in all_chunks]

    # Batch in groups of 20
    all_embeddings: list[list[float]] = []
    batch_size = 20
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embs = generate_embeddings_batch(batch)
        all_embeddings.extend(embs)
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)}")

    print("[RAG] Storing chunks in pgvector...")
    stored, skipped = repository.store_chunks(all_chunks, all_embeddings)
    print(f"[RAG] Done! Stored: {stored}, Skipped (duplicates): {skipped}")
    return stored, skipped
