# DBdiver

DBdiver is an AI-powered PostgreSQL assistant with:
- A FastAPI backend that retrieves DB schema context, generates SQL with an LLM, executes SQL, and summarizes results.
- A Streamlit frontend chat UI for asking natural-language questions.

## Features
- Natural language to SQL generation.
- Schema-aware retrieval using embeddings + Chroma vector database.
- PostgreSQL query execution via SQLAlchemy.
- Human-readable answer summaries from query results.
- Deployable as two services (backend + frontend) using `render.yaml`.

## Project Structure

```text
backend/
  main.py             # FastAPI app and /query endpoint
  models.py           # Pydantic request/response models
  settings.py         # Environment-variable based configuration
  llm_engine.py       # LLM calls for SQL generation and result summarization
  db_runner.py        # SQL execution against PostgreSQL
  schema_indexer.py   # PostgreSQL schema extraction + chunking + Chroma indexing
  rag_pipeline.py     # Retrieval of relevant schema chunks
frontend/
  app.py              # Streamlit chat UI
render.yaml           # Render blueprint for backend + frontend
dockerfile            # Container config for backend
requirements.txt      # Python dependencies
DEPLOYMENT.md         # Deployment instructions
```

## How It Works
1. User asks a question in Streamlit.
2. Frontend sends `POST /query` with `question` and `db_url`.
3. Backend introspects PostgreSQL schema and indexes chunks in Chroma (or reuses cached index).
4. Relevant schema chunks are retrieved using embedding similarity.
5. LLM generates SQL from the user question + retrieved schema context.
6. SQL is executed against the provided PostgreSQL database.
7. LLM summarizes the raw rows into concise natural language.
8. Frontend shows summary and expandable generated SQL.

## Requirements
- Python 3.10+
- A reachable PostgreSQL database
- OpenAI API key (`OPENAI_API_KEY`)

## Installation (Local)

1. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment Variables

Backend reads configuration from environment variables (`backend/settings.py`):

- `OPENAI_API_KEY` (required): OpenAI API key.
- `EMBEDDING_MODEL` (optional, default: `all-MiniLM-L6-v2`)
- `VECTOR_DB_PATH` (optional, default: `./vectordb`)
- `TOP_K` (optional, default: `5`)

Frontend:
- `BACKEND_URL` (optional, default: `http://localhost:8000`)

Example:

```bash
export OPENAI_API_KEY="your_key_here"
export EMBEDDING_MODEL="all-MiniLM-L6-v2"
export VECTOR_DB_PATH="./vectordb"
export TOP_K=5
export BACKEND_URL="http://localhost:8000"
```

## Run Locally

### 1) Start Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Check:
- `http://localhost:8000/` (health)
- `http://localhost:8000/docs` (Swagger)

### 2) Start Frontend

In a second terminal:

```bash
streamlit run frontend/app.py
```

Open the Streamlit URL shown in terminal (usually `http://localhost:8501`).

## API

### `GET /`
Health check.

Response:

```json
{"status": "ok"}
```

### `POST /query`
Generate SQL, execute it, and return machine + human-friendly output.

Request body:

```json
{
  "question": "How many users signed up last month?",
  "db_url": "postgresql://user:password@host:5432/dbname"
}
```

Success response shape:

```json
{
  "sql": "SELECT ...",
  "result": [{"...": "..."}],
  "formatted_result": "Plain-language summary..."
}
```

Error response shape:

```json
{
  "sql": "SELECT ...",
  "error": "Error message"
}
```

## Deployment

### Render (recommended)
This repo includes `render.yaml` for two services:
- `dbdiver-backend`
- `dbdiver-frontend`

Steps:
1. Push repository to GitHub.
2. In Render, create a new Blueprint and select the repo.
3. Set env vars:
   - Backend: `OPENAI_API_KEY`
   - Frontend: `BACKEND_URL` set to backend public URL
4. Deploy both services.

Notes:
- Backend uses persistent disk for vector DB at `/var/data/vectordb`.
- Free tier services may cold-start or sleep.

## Docker (Backend)

Build:

```bash
docker build -t dbdiver-backend -f dockerfile .
```

Run:

```bash
docker run -p 8000:8000 -e OPENAI_API_KEY="your_key_here" dbdiver-backend
```

## Security Notes
- Do not commit secrets to source code.
- Use environment variables for API keys.
- `backend/config.py` is git-ignored and should not contain active production secrets.
- If any key was exposed, rotate/revoke it immediately.

## Troubleshooting
- `OPENAI_API_KEY is not set`: export key before starting backend.
- Connection errors in frontend: verify `BACKEND_URL` and backend service health.
- SQL execution failures: ensure `db_url` is valid and reachable from backend runtime.
- Empty or weak answers: verify schema retrieval and increase `TOP_K` if needed.
- Slow first query: embedding model and vector index warm-up can add latency.

## Limitations
- Current schema indexer enforces PostgreSQL only.
- SQL safety guardrails are minimal; use a restricted DB user with least privilege.
- Very large query results are summarized from a truncated preview.

## Future Improvements
- Add SQL validation and allowlist/denylist checks before execution.
- Add retries using `fix_sql` path on SQL errors.
- Add authentication and rate limiting to backend endpoints.
- Add tests for API, schema indexing, and SQL generation pipeline.

## License
No license file is currently present in this repository. Add one if you plan to distribute this project.
