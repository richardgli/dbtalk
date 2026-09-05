from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
import psycopg2
import re
import os
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def get_schema_text():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
            """
        )
        rows = cur.fetchall()
    conn.close()
    return "\n".join(f"{t}.{c} ({d})" for t, c, d in rows)


def get_devices_context():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM devices;
            """
        )
        rows = cur.fetchall()
    conn.close()
    return "\n".join(f"id={i}, name={n}, lat={la}, lon={lo}, tz={tz}" for i, n, la, lo, tz in rows)


DENY_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE)\b", re.I)


def sanitize_sql(query: str) -> str:
    q = query.strip().rstrip(";")
    if not q.lower().startswith("select") and not q.lower().startswith("with"):
        raise ValueError("Only SELECT statements are allowed")
    if DENY_RE.search(q):
        raise ValueError("DML/DDL detected. Only read-only queries are allowed.")
    return q


@tool(description="Executes the given SQL query")
def execute_sql(query: str) -> str:
    q = sanitize_sql(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(q)
            if cur.description:
                rows = cur.fetchall()
                return str(rows) if rows else "NO_DATA"
            return "NO_DATA"
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()


system_prompt = f"""You are an analyst for a TimescaleDB database.
Schema (do not invent columns/tables):
{get_schema_text()}

Devices reference table (device names map to device IDs):
{get_devices_context()}

Rules:
- Think step-by-step.
- When you need data, call execute_sql with ONE query.
- You can only use read-only queries: no INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE/TRUNCATE.
- If the tool returns 'Error:', revise the SQL and try again.
- Limit to 5 attempts. Say plainly when you are unsuccessful.
- If a query runs successfully but returns no rows, answer "NO_DATA rather than guessing.
"""

model = ChatOllama(
    model="llama3.1",
    base_url=os.getenv("OLLAMA_URL"),
    temperature=0,
)

agent = create_agent(
    model=model,
    tools=[execute_sql],
    system_prompt=system_prompt,
)
