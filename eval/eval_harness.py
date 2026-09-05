import json
import re
from typing import Any, List, Tuple
from dataclasses import dataclass

from agent import agent_setup

DEVICE_NAMES = {
    1: "seattle", 2: "sao paulo", 3: "sydney", 4: "london", 5: "paris", 6: "victoria",
}

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
    value_matched = any(abs(n - value) <= tolerance for n in numbers)

    if id_mentioned and value_matched:
        return "pass", f"device '{name}' and value ~{value} received"
    elif id_mentioned:
        return "review", f"device '{name}' mentioned but value {value} not found"
    else:
        return "fail", f"device '{name}' not mentioned"


def check_boolean(expected: bool, response: str) -> Tuple[str, str]:
    negations = ["no", "not", "offline", "wasn't", "did not", "false"]
    affirmations = ["yes", "online", "was", "did", "true"]
    resp_lower = response.lower()

    has_negation = any(word in resp_lower for word in negations)
    has_affirmation = any(word in resp_lower for word in affirmations)

    if expected is False and has_negation and not has_affirmation:
        return "pass", "negation detected, matches expected False"
    elif expected is True and has_affirmation and not has_negation:
        return "pass", "affirmation detected, matches expected True"
    else:
        return "review", "ambiguous or conflicting signals in response"


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


def get_agent_response(question: dict):
    agent = agent_setup()
    return agent.invoke({"messages": [{"role": "user", "content": question}]})


def run_eval(eval_set_path: str, agent_fn) -> List[EvalResult]:
    questions = load_eval_set(eval_set_path)
    results = []

    for q in questions:
        print(f"Question {q["id"]}: {q["question"]}")
        response = agent_fn(q["question"])

        final_text = next(
            msg.content for msg in reversed(response["messages"])
            if msg.type == "ai" and msg.content
        )

        print(f"Answer: {final_text}\n")
        verdict, reason = check_answer(q, final_text)
        results.append(EvalResult(
            id=q["id"], question=q["question"], expected=q["expected_answer"], agent_response=response, verdict=verdict, reason=reason,
        ))

    return results


def print_summary(results: List[EvalResult]):
    counts = {"pass": 0, "fail": 0, "review": 0}
    for r in results:
        counts[r.verdict] += 1
        print(f"[{r.verdict.upper():6}] {r.id}: {r.reason}")

    print(f"\n{counts['pass']} passed, {counts['fail']} failed, {counts["review"]} need review out of {len(results)}")


if __name__ == "__main__":
    results = run_eval("eval/eval_set.json", get_agent_response)
    print_summary(results)