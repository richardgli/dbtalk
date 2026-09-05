from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
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
                if not rows:
                    return "NO_DATA"
                if len(rows) > 20:
                    return (f"Query returned {len(rows)} rows."
                            f"Rewrite the query to use COUNT(*), EXISTS(...), or another aggregate "
                            f"so it returns a single summary value instead of raw rows. "
                            f"First 3 rows for reference: {rows[:3]}")
                return str(rows) if rows else "NO_DATA"
            return "NO_DATA"
    except Exception as e:
        return f"Error: {e}"
    finally:
        conn.close()


def agent_setup() -> CompiledStateGraph:
    system_prompt = f"""You are an analyst for a TimescaleDB database.
    Schema (do not invent columns/tables):
    {get_schema_text()}

    Devices reference table (device names map to device IDs):
    {get_devices_context()}

    The device_status table logs state CHANGES (rows only when online/offline flips), not continuous readings.

    Rules:
    - Think step-by-step.
    - When you need data, call execute_sql with ONE query.
    - You can only use read-only queries: no INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE/TRUNCATE.
    - If the tool returns 'Error:', read the error message, revise the SQL and try again.
    - If a query returns a negative time value, revise the SQL and try again. Time must be positive.
    - Limit to 5 attempts. Say plainly when you are unsuccessful.
    - Your final answer must always state the exact numeric value(s) returned by the query. For example, if asked "which device had the highest average temperature," answer "Device X had the highest average temperature at Y.YY°C".
    - For yes/no or true/false questions, state the answer as an unambiguous single word or short phrase at the start of your response.
    - If a query returns NO_DATA, say so plainly. NEVER guess or infer an answer you don't have direct evidence for.
    - Before writing any query that filters by a named device/city, check whether that name appears in the Device reference table above. 
    """

    model = ChatOllama(
        model="llama3.1",
        base_url=os.getenv("OLLAMA_URL"),
        temperature=0,
    )

    return create_agent(
        model=model,
        tools=[execute_sql],
        system_prompt=system_prompt,
    )
