from fastapi import FastAPI

from backend.models import QueryRequest
from backend.rag_pipeline import retrieve_schema
from backend.gemini_engine import generate_sql, humanize_result
from backend.db_runner import PostgresRunner
app = FastAPI()


@app.post("/query")

def query_db(req: QueryRequest):

    print(f"[Main] Received query request: {req.question} for DB: {req.db_url}")


    schema = retrieve_schema(req.question, req.db_url)

    schema_context = "\n".join(schema)

    sql = generate_sql(req.question, schema_context)

    runner = PostgresRunner(req.db_url)

    try:

        result = runner.run_sql(sql)
        print(f"[Main] SQL execution result: {result}")
        formatted_result = humanize_result(req.question, sql, result, max_chars=500000)

        return {
            "sql": sql,
            "result": result,
            "formatted_result": formatted_result
        }

    except Exception as e:

        return {
            "sql": sql,
            "error": str(e)
        }