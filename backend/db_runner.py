from sqlalchemy import create_engine, text

class PostgresRunner:

    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)

    def run_sql(self, query):
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            rows = [dict(r) for r in result.mappings()]
            return rows


# if __name__ == "__main__":
#     CONNECTION_STRING = "postgresql://postgres:krrish%40%4010852@db.yxjwycpadvtcmgrvycla.supabase.co:5432/postgres"

#     runner = PostgresRunner(CONNECTION_STRING)

#     query = "SELECT * FROM jobs_data LIMIT 5;"
#     print(f"Running query: {query}\n")

#     try:
#         results = runner.run_sql(query)
#         print(f"Fetched {len(results)} row(s):")
#         for row in results:
#             print(row)
#     except Exception as e:
#         print(f"Error: {e}")