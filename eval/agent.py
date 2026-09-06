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
            SELECT id, name, latitude, longitude
            FROM devices;
            """
        )
        rows = cur.fetchall()
    conn.close()
    return "\n".join(f"id={i}, name={n}, lat={la}, lon={lo}" for i, n, la, lo in rows)


def get_few_shots():
    DOWNTIME_CALCULATION="""
    Question: What was the total downtime for the Sydney device in hours?
    SQL: WITH time_pairs AS (SELECT time, online, LEAD(time) OVER (ORDER BY time) AS next_time, LEAD(online) OVER (ORDER BY time) AS next_online FROM device_status WHERE device_id = 3) SELECT ROUND(CAST(SUM(EXTRACT(EPOCH FROM (next_time - time)) / 3600) AS NUMERIC), 2) FROM time_pairs WHERE next_online IS TRUE AND online IS FALSE;
    """

    STATUS_CHECK="""
    Question: Was the Paris device online at 5:00 PM UTC on August 11, 2026?
    SQL: SELECT online FROM device_status WHERE device_id = 5 AND time <= '2026-08-11 17:00:00' ORDER BY time DESC LIMIT 1;
    """

    DATA_CHECK="""
    Question: Did the Seattle device have any readings during a period when it should have been offline?
    SQL: WITH time_pairs AS (SELECT time, online, LEAD(time) OVER (ORDER BY time) AS next_time, LEAD(online) OVER (ORDER BY time) AS next_online FROM device_status WHERE device_id = 1), outage_events AS (SELECT time, next_time FROM time_pairs WHERE next_online IS TRUE AND online IS FALSE) SELECT r.* FROM sensor_readings r JOIN outage_events o ON r.time >= o.time AND r.time < o.next_time WHERE r.device_id = 1;
    """

    return f"{DOWNTIME_CALCULATION}\n{STATUS_CHECK}\n{DATA_CHECK}\n"


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

    Devices reference table:
    {get_devices_context()}

    The device_status table logs state CHANGES (rows only when online/offline flips), not continuous readings.

    Answer format:
    Question: (rewrite question)
    SQL: (your queries that you used to reach your answer)
    SQL Result: (the result of the queries)
    Answer: (your final answer)

    When answering a database question:
    - Think step-by-step. When you need data, call execute_sql with ONE query. When querying with device information, ensure that it exists in the devices table.
    - You cannot use INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/REPLACE/TRUNCATE in your query.
    - If the tool returns 'Error:', read the error message, revise the SQL and try again.
    - Time and distance values CANNOT be negative. Revise your SQL to ensure that you get positive values.
    - Your final answer must always state the exact numeric value(s) returned by the query. For example, if asked "which device had the highest average temperature," answer "Device X had the highest average temperature at Y.YY°C".
    - Limit to 5 attempts. Say plainly when you are unsuccessful.

    Examples:
    {get_few_shots()}
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
