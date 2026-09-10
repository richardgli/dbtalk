import ast
import re

def parse_agent_response(state: dict):
    messages = state["messages"]

    sql = ""
    raw_results = None

    for message in messages:
        if getattr(message, "tool_calls", None):
            sql = message.tool_calls[0]["args"].get("query", "")
        if message.__class__.__name__ == "ToolMessage":
            raw_results = message.content

    final_content = messages[-1].content
    match = re.search(r"Answer:\s*(.*)", final_content, re.DOTALL)
    answer = match.group(1).strip() if match else final_content

    results = []
    if raw_results:
        try:
            rows = ast.literal_eval(raw_results)
            results = [{"result": row[0] if len(row) == 1 else dict(enumerate(row)) for row in rows}]
        except (ValueError, SyntaxError):
            results = []

    return {"answer": answer, "sql": sql, "results": results}