from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 1536


@dataclass
class RetrievedChunk:
    title: str
    content: str
    category: str
    source: str
    similarity: float


@dataclass
class Chunk:
    title: str
    content: str
    category: str
    source: str
    content_hash: str


from app.config import get_db_connection_string





class PostgresKnowledgeRepository:
    def __init__(self, connection_string_provider: Callable[[], str] = get_db_connection_string):
        self.get_dsn = connection_string_provider

    def ensure_schema(self) -> None:
        """Create the pgvector extension and knowledge_chunks table if they don't exist."""
        conn = psycopg2.connect(self.get_dsn())
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS knowledge_chunks (
                        id SERIAL PRIMARY KEY,
                        content_hash TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category TEXT NOT NULL,
                        source TEXT NOT NULL DEFAULT 'HomePlannerAI Knowledge Base',
                        embedding vector({EMBEDDING_DIM}),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding
                    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 10);
                """)
        finally:
            conn.close()
        logger.info("Knowledge schema ensured.")

    def store_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> tuple[int, int]:
        """Store chunks with embeddings into pgvector."""
        conn = psycopg2.connect(self.get_dsn())
        try:
            with conn.cursor() as cur:
                stored = 0
                skipped = 0
                for chunk, emb in zip(chunks, embeddings):
                    emb_str = "[" + ",".join(str(x) for x in emb) + "]"
                    try:
                        cur.execute(
                            """
                            INSERT INTO knowledge_chunks (content_hash, title, content, category, source, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s::vector)
                            ON CONFLICT (content_hash) DO NOTHING
                            """,
                            (chunk.content_hash, chunk.title, chunk.content, chunk.category, chunk.source, emb_str)
                        )
                        if cur.rowcount > 0:
                            stored += 1
                        else:
                            skipped += 1
                    except Exception as e:
                        logger.warning(f"Failed to store chunk {chunk.content_hash}: {e}")
                        conn.rollback()
                        skipped += 1
                conn.commit()
        finally:
            conn.close()
        logger.info(f"Stored {stored} chunks, skipped {skipped} (already exist).")
        return stored, skipped

    def search(self, query_embedding: list[float], top_k: int, category_filter: str | None, similarity_threshold: float) -> list[RetrievedChunk]:
        """Semantic search against the knowledge base."""
        emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
        conn = psycopg2.connect(self.get_dsn())
        try:
            with conn.cursor() as cur:
                if category_filter:
                    cur.execute(
                        """
                        SELECT title, content, category, source,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM knowledge_chunks
                        WHERE category = %s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (emb_str, category_filter, emb_str, top_k)
                    )
                else:
                    cur.execute(
                        """
                        SELECT title, content, category, source,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM knowledge_chunks
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (emb_str, emb_str, top_k)
                    )
                
                results = []
                for row in cur.fetchall():
                    title, content, category, source, similarity = row
                    if similarity >= similarity_threshold:
                        results.append(RetrievedChunk(
                            title=title,
                            content=content,
                            category=category,
                            source=source,
                            similarity=round(float(similarity), 4),
                        ))
        finally:
            conn.close()
        return results
