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


def _dotnet_to_psycopg2(dotnet_str: str) -> str:
    """Convert .NET-style connection string to psycopg2 DSN."""
    parts: dict[str, str] = {}
    for segment in dotnet_str.split(';'):
        segment = segment.strip()
        if '=' in segment:
            k, v = segment.split('=', 1)
            parts[k.strip().lower()] = v.strip()

    host = parts.get('host', 'localhost')
    port = parts.get('port', '5432')
    dbname = parts.get('database', 'postgres')
    user = parts.get('username', 'postgres')
    password = parts.get('password', '')
    sslmode = 'require' if 'require' in parts.get('ssl mode', '').lower() else 'prefer'

    return f"host={host} port={port} dbname={dbname} user={user} password={password} sslmode={sslmode}"


def get_db_connection_string() -> str:
    """Build a psycopg2-compatible DSN from the .env DATABASE_CONNECTION_STRING."""
    for env_path in [
        os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'HousePlanner.API', '.env'),
    ]:
        if not os.path.exists(env_path):
            continue
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_CONNECTION_STRING='):
                    raw = line.split('=', 1)[1].strip().strip('"\'')
                    return _dotnet_to_psycopg2(raw)

    raw = os.getenv('DATABASE_CONNECTION_STRING', '')
    if raw:
        return _dotnet_to_psycopg2(raw)

    raise RuntimeError("DATABASE_CONNECTION_STRING not found in .env or environment.")


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
