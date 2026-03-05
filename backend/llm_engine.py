import json
from openai import OpenAI
from backend.config import OPENAI_API_KEY

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_sql(question, schema):
    prompt = f"""
    You are an expert SQL generator.
    Database Schema:
    {schema}
    Convert the following question into SQL.
    Question:
    {question}
    Return ONLY SQL.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs only valid SQL code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0  # Keeping it at 0 ensures consistent SQL output
        )
        # Clean the response to remove potential markdown backticks
        return response.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        return f"Error generating SQL: {str(e)}"

def fix_sql(question, schema, sql, error):
    prompt = f"""
You are an expert PostgreSQL SQL generator.

IMPORTANT:
- The database is PostgreSQL.
- Do NOT use MySQL syntax like SHOW TABLES.
- Use PostgreSQL syntax only.

Database Schema:
{schema}

Convert the following natural language question into a PostgreSQL SQL query.

Question:
{question}

Return ONLY the SQL query.
"""

    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a SQL debugging expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        return f"Error fixing SQL: {str(e)}"


def humanize_result(question, sql, db_result, max_chars: int = 8000):
    raw_preview = json.dumps(db_result, default=str)
    if len(raw_preview) > 4000:
        raw_preview = raw_preview[:8000]

    prompt = f"""
You are a data assistant.

User question:
{question}

Executed SQL:
{sql}

Database output (JSON):
{raw_preview}

Create a concise, easy-to-read summary for a non-technical user.
Rules:
- Max {max_chars} characters.
- Plain text only.
- Mention key values/counts if available.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You summarize SQL results clearly and briefly."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        text_out = response.choices[0].message.content.strip()
        return text_out[:max_chars]
    except Exception as e:
        fallback = f"Could not format response. Raw rows returned: {len(db_result) if isinstance(db_result, list) else 'unknown'}. Error: {str(e)}"
        return fallback[:max_chars]