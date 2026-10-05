import time
import json
import re
from typing import Any, List, Tuple
from dataclasses import dataclass

from langchain_core.callbacks import BaseCallbackHandler

from agent.agent_setup import agent_setup

DEVICE_NAMES = {
    1: "seattle", 2: "sao paulo", 3: "sydney", 4: "london", 5: "paris", 6: "victoria",
}

class MetricsCallback(BaseCallbackHandler):
    def __init__(self):
        self.llm_start = None
        self.tool_start = None
        self.llm_calls = []
        self.tool_calls = []

    def on_llm_start(self, serialized, prompts, **kwargs):
        self.llm_start = time.perf_counter()

    def on_llm_end(self, response, **kwargs):
        elapsed = time.perf_counter() - self.llm_start

        self.llm_calls.append({
            "latency": elapsed,
            "usage": response.llm_output.get("token_usage", {})
                if response.llm_output else {}
        })

    def on_tool_start(self, serialized, input_str, **kwargs):
        self.tool_start = time.perf_counter()

    def on_tool_end(self, output, **kwargs):
        elapsed = time.perf_counter() - self.tool_start

        self.tool_calls.append({
            "latency": elapsed,
            "output": str(output)
        })

@dataclass
class EvalResult:
    id: str
    question: str
    expected: Any
    agent_response: str
    verdict: str
    reason: str

def load_eval_set(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)["questions"]


# ---------------------------------------------------------------------------
# Check agent answer shapes
# ---------------------------------------------------------------------------

def check_numeric(expected: float, response: str, tolerance: float = 0.5) -> EvalResult:
    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", response)]
    for n in numbers:
        if abs(n - expected) <= tolerance:
            return "pass", f"returned {n}, within {tolerance} of {expected}"
    return "review", f"no number within tolerance received; seen {numbers}"


def check_device_answer(expected: list, response: str, device_names: dict, tolerance: float = 0.5) -> Tuple[str, str]:
    device_id, value = expected
    name = device_names.get(device_id, "").lower()
    id_mentioned = str(device_id) in response or name in response.lower()

    numbers = [float(n) for n in re.findall(r"-?\d+\.?\d*", response)]
    if value:
        value_matched = any(abs(n - value) <= tolerance for n in numbers)
    else:
        value_matched = False

    if id_mentioned and value and value_matched:
        return "pass", f"device '{name}' and value ~{value} received"
    elif id_mentioned and value and not value_matched:
        return "review", f"device '{name}' mentioned but value {value} not found"
    elif id_mentioned and not value:
        return "pass", f"device '{name}' received"
    else:
        return "fail", f"device '{name}' not mentioned"


def check_boolean(expected: bool, response: str) -> Tuple[str, str]:
    match = re.match(r"^\s*ANSWER:\s*(YES|NO|UNKNOWN)\b", response, re.IGNORECASE)
    if not match:
        return "review", "no ANSWER: token found at start of response"

    answer = match.group(1).upper()
    if answer == "UNKNOWN":
        return "review", "model reported UNKNOWN — check if NO_DATA was legitimate"

    got = (answer == "YES")
    if got == expected:
        return "pass", f"ANSWER: {answer} matches expected {expected}"
    return "fail", f"ANSWER: {answer} does not match expected {expected}"


def check_no_data(response: str) -> Tuple[str, str]:
    no_data_phrases = ["no data", "don't have", "no device", "not available", "no information"]
    resp_lower = response.lower()
    if any(phrase in resp_lower for phrase in no_data_phrases):
        return "pass", "correctly indicated no data available"

    if re.search(r"-?\d+\.?\d*\s*(degrees|°|c\b)", resp_lower):
        return "fail", "appears to have hallucinated a temperature value"
    return "review", "unclear whether agent acknowledged missing data"


def check_answer(q: dict, response: str) -> Tuple[str, str]:
    expected = q["expected_answer"]
    if expected == "NO_DATA":
        return check_no_data(response)

    if isinstance(expected, bool):
        return check_boolean(expected, response)

    if isinstance(expected, list):
        return check_device_answer(expected, response, DEVICE_NAMES)

    if isinstance(expected, (int, float)):
        return check_numeric(float(expected), response)

    return "review", "unrecognized expected_answer type"


def get_agent_response(question: str, session_id: str):
    metrics = MetricsCallback()
    config = {"configurable": {"thread_id": session_id}, "callbacks": [metrics], "recursion_limit": 5}
    agent = agent_setup()
    start = time.perf_counter()
    results = agent.invoke({
        "messages": [{"role": "user", "content": question}]},
        config=config,
    )
    total_time = time.perf_counter() - start
    with open("output.txt", "a", encoding="utf-8") as file:
        file.write(f"\nTotal: {total_time:.2f}s")
        file.write(f"\nLLM calls: {len(metrics.llm_calls)}")
        file.write(f"\nTool calls: {len(metrics.tool_calls)}")

        for i, call in enumerate(metrics.llm_calls):
            file.write(f"\nLLM {i + 1}: {call['latency']:.2f}s")

        for i, call in enumerate(metrics.tool_calls):
            file.write(f"\nTool {i + 1}: {call['latency']:.2f}s")
    return results


def run_eval(eval_set_path: str, agent_fn) -> List[EvalResult]:
    questions = load_eval_set(eval_set_path)
    results = []

    for q in questions:
        with open("output.txt", "a", encoding="utf-8") as file:
            file.write(f"\n\nQuestion {q["id"]}: {q["question"]}")
            response = agent_fn(q["question"], 1)

            final_text = next(
                msg.content for msg in reversed(response["messages"])
                if msg.type == "ai" and msg.content
            )

            file.write(f"\n\nAnswer: {final_text}\n")
        verdict, reason = check_answer(q, final_text)
        results.append(EvalResult(
            id=q["id"], question=q["question"], expected=q["expected_answer"], agent_response=response, verdict=verdict, reason=reason,
        ))

    return results


def print_summary(results: List[EvalResult]):
    counts = {"pass": 0, "fail": 0, "review": 0}
    with open("output.txt", "a", encoding="utf-8") as file:
        for r in results:
            counts[r.verdict] += 1
            file.write(f"\n\n[{r.verdict.upper():6}] {r.id}: {r.reason}")

        file.write(f"\n{counts['pass']} passed, {counts['fail']} failed, {counts["review"]} need review out of {len(results)}")


if __name__ == "__main__":
    results = run_eval("eval/eval_set.json", get_agent_response)
    print_summary(results)