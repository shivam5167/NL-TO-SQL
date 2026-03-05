from sentence_transformers import SentenceTransformer
from backend.config import EMBEDDING_MODEL, TOP_K
from backend.schema_indexer import index_database_schema

model = SentenceTransformer(EMBEDDING_MODEL)


def retrieve_schema(query, db_url):

    collection = index_database_schema(db_url, model)

    query_embedding = model.encode([query])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=TOP_K
    )

    retrieved_chunks = results.get("documents", [[]])[0]
    print(f"[RAG] Retrieved {len(retrieved_chunks)} chunk(s) for query: {query}")
    for i, chunk in enumerate(retrieved_chunks, start=1):
        print(f"\n[RAG] Retrieved Chunk {i}/{len(retrieved_chunks)}\n{chunk}\n")

    return retrieved_chunks