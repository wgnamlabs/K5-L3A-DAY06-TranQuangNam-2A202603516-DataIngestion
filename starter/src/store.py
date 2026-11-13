"""Persistent exact cosine retrieval in PostgreSQL + pgvector."""

from __future__ import annotations

import math
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int,
                 model_name: str = "google/embeddinggemma-2") -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        if dimensions not in (128, 256, 512, 768):
            raise ValueError("Unsupported embedding dimensions")
        self.database_url = database_url
        self.dimensions = dimensions
        self.model_name = model_name

    def _vector(self, values: list[float]) -> str:
        if len(values) != self.dimensions or not all(math.isfinite(float(x)) for x in values):
            raise ValueError(f"Expected {self.dimensions} finite vector values")
        return "[" + ",".join(repr(float(value)) for value in values) + "]"

    def create_schema(self) -> None:
        """Create an exact-search table and check its vector dimension."""
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS ingestion_chunks (
                        strategy text NOT NULL,
                        chunk_id text NOT NULL,
                        document_id text NOT NULL,
                        source text NOT NULL,
                        page integer NOT NULL CHECK (page > 0),
                        audience text NOT NULL CHECK (audience IN ('teachers', 'students')),
                        text text NOT NULL,
                        metadata jsonb NOT NULL,
                        model_name text NOT NULL,
                        embedding vector({self.dimensions}) NOT NULL,
                        PRIMARY KEY (strategy, chunk_id)
                    )
                """)
                cursor.execute("""
                    SELECT format_type(a.atttypid, a.atttypmod)
                    FROM pg_attribute a
                    WHERE a.attrelid = 'ingestion_chunks'::regclass
                      AND a.attname = 'embedding' AND NOT a.attisdropped
                """)
                actual = cursor.fetchone()[0]
                if actual != f"vector({self.dimensions})":
                    raise ValueError(f"Existing ingestion_chunks has {actual}; expected vector({self.dimensions})")
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS ingestion_chunks_strategy_audience_idx
                    ON ingestion_chunks (strategy, audience)
                """)

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Replace one strategy's snapshot atomically; remove obsolete chunks."""
        if strategy not in ("A", "B"):
            raise ValueError("Only A and B store embeddings; C reuses B")
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors have different lengths")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("Duplicate chunk IDs")
        rows = []
        for chunk, vector in zip(chunks, vectors):
            audience = chunk.metadata.get("audience")
            if audience not in ("teachers", "students") or chunk.page < 1:
                raise ValueError(f"Invalid metadata for {chunk.chunk_id}")
            rows.append((strategy, chunk.chunk_id, chunk.document_id, chunk.source, chunk.page,
                         audience, chunk.text, Jsonb(chunk.metadata), self.model_name,
                         self._vector(vector)))
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO ingestion_chunks
                    (strategy, chunk_id, document_id, source, page, audience, text,
                     metadata, model_name, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                    ON CONFLICT (strategy, chunk_id) DO UPDATE SET
                      document_id=EXCLUDED.document_id,
                      source=EXCLUDED.source,
                      page=EXCLUDED.page,
                      audience=EXCLUDED.audience,
                      text=EXCLUDED.text,
                      metadata=EXCLUDED.metadata,
                      model_name=EXCLUDED.model_name,
                      embedding=EXCLUDED.embedding
                """, rows)
                cursor.execute("""
                    DELETE FROM ingestion_chunks
                    WHERE strategy = %s AND NOT (chunk_id = ANY(%s::text[]))
                """, (strategy, [chunk.chunk_id for chunk in chunks]))

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Rank by exact cosine distance, optionally restricting audience in SQL."""
        if strategy not in ("A", "B"):
            raise ValueError("C must search B with an optional audience filter")
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if filters and (set(filters) != {"audience"} or filters["audience"] not in ("teachers", "students")):
            raise ValueError("Only audience=teachers|students may be filtered")
        vector = self._vector(query_vector)
        where = "strategy = %s AND model_name = %s"
        params: list[Any] = [vector, strategy, self.model_name]
        if filters:
            where += " AND audience = %s"
            params.append(filters["audience"])
        params.append(top_k)
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT chunk_id, document_id, source, page, audience, text, metadata,
                           1 - (embedding <=> %s::vector) AS score
                    FROM ingestion_chunks
                    WHERE {where}
                    ORDER BY score DESC, chunk_id
                    LIMIT %s
                """, params)
                return [dict(zip(("chunk_id", "document_id", "source", "page", "audience",
                                  "text", "metadata", "score"), row)) for row in cursor.fetchall()]

    def count(self, strategy: str) -> int:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM ingestion_chunks WHERE strategy = %s", (strategy,))
                return cursor.fetchone()[0]
