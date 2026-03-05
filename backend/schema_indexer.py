import hashlib
from typing import List

import chromadb
from sqlalchemy import create_engine, text

from backend.config import VECTOR_DB_PATH

client = chromadb.PersistentClient(path=VECTOR_DB_PATH)

SYSTEM_SCHEMAS = {"information_schema", "pg_catalog"}


def _collection_name_for_db(db_url: str) -> str:
    db_hash = hashlib.sha1(db_url.encode("utf-8")).hexdigest()[:16]
    return f"schema_{db_hash}"


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _table_schema_text(conn, table_name: str, schema_name: str) -> str:
    columns = conn.execute(
        text(
            """
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = :schema_name AND table_name = :table_name
            ORDER BY ordinal_position;
            """
        ),
        {"schema_name": schema_name, "table_name": table_name},
    ).mappings().all()

    primary_keys = conn.execute(
        text(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = :schema_name
              AND tc.table_name = :table_name
            ORDER BY kcu.ordinal_position;
            """
        ),
        {"schema_name": schema_name, "table_name": table_name},
    ).mappings().all()
    pk_set = {row["column_name"] for row in primary_keys}

    foreign_keys = conn.execute(
        text(
            """
            SELECT
                kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = :schema_name
              AND tc.table_name = :table_name
            ORDER BY kcu.ordinal_position;
            """
        ),
        {"schema_name": schema_name, "table_name": table_name},
    ).mappings().all()

    indexes = conn.execute(
        text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = :schema_name
              AND tablename = :table_name
            ORDER BY indexname;
            """
        ),
        {"schema_name": schema_name, "table_name": table_name},
    ).mappings().all()

    lines = [f"Table: {schema_name}.{table_name}", "Columns:"]
    for col in columns:
        data_type = col["data_type"]
        udt_name = col["udt_name"]
        pg_type = udt_name if data_type == "USER-DEFINED" else data_type

        col_line = f"- {col['column_name']} {pg_type}"
        if col["column_name"] in pk_set:
            col_line += " PRIMARY KEY"
        col_line += " NOT NULL" if col["is_nullable"] == "NO" else " NULLABLE"
        if col["column_default"] is not None:
            col_line += f" DEFAULT {col['column_default']}"
        lines.append(col_line)

    if foreign_keys:
        lines.append("Foreign Keys:")
        for fk in foreign_keys:
            lines.append(
                f"- ({fk['column_name']}) -> "
                f"{fk['foreign_table_schema']}.{fk['foreign_table_name']}({fk['foreign_column_name']})"
            )

    if indexes:
        lines.append("Indexes:")
        for idx in indexes:
            lines.append(f"- {idx['indexname']}: {idx['indexdef']}")

    return "\n".join(lines)


def _extract_schema_chunks(db_url: str) -> List[str]:
    engine = create_engine(db_url)

    if engine.dialect.name != "postgresql":
        raise ValueError("Only PostgreSQL databases are supported.")

    with engine.connect() as conn:
        tables = conn.execute(
            text(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type = 'BASE TABLE'
                  AND table_schema NOT IN ('information_schema', 'pg_catalog')
                ORDER BY table_schema, table_name;
                """
            )
        ).mappings().all()

        table_texts: List[str] = []
        for t in tables:
            table_texts.append(_table_schema_text(conn, t["table_name"], t["table_schema"]))

    chunks: List[str] = []
    for table_text in table_texts:
        chunks.extend(_chunk_text(table_text))

    if not chunks:
        chunks = ["No user tables found in the connected database."]

    return chunks


def index_database_schema(db_url: str, embedding_model, force_reindex: bool = False):
    collection_name = _collection_name_for_db(db_url)

    if force_reindex:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(collection_name)
    if collection.count() > 0 and not force_reindex:
        print(f"[SchemaIndexer] Using existing collection '{collection_name}' with {collection.count()} chunks")
        return collection

    schema_chunks = _extract_schema_chunks(db_url)
    print(f"[SchemaIndexer] Upserting {len(schema_chunks)} chunks into '{collection_name}'")
    for i, chunk in enumerate(schema_chunks, start=1):
        print(f"\n[SchemaIndexer] Chunk {i}/{len(schema_chunks)}\n{chunk}\n")

    embeddings = embedding_model.encode(schema_chunks).tolist()
    ids = [f"chunk_{i}" for i in range(len(schema_chunks))]

    collection.upsert(
        documents=schema_chunks,
        embeddings=embeddings,
        ids=ids,
    )
    return collection