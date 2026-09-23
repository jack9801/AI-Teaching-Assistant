from __future__ import annotations

import os
import re
import uuid
from typing import Literal, TypedDict

from langgraph.graph import END, StateGraph

from .prompts import SAFETY_BLOCK_MESSAGE, SOCRATIC_SYSTEM_PROMPT
from .solver import StepEvaluation, extract_latest_equation, verify_step


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class TutorState(TypedDict, total=False):
    request_id: str
    messages: list[ChatMessage]
    blocked: bool
    safety_reason: str
    equation: str
    math_evaluation: StepEvaluation | None
    response: str
    teacher_thoughts: str


_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"(just|only)\s+(give|tell)\s+(me\s+)?(the\s+)?answer", re.I),
    re.compile(r"give\s+me\s+(the\s+)?final\s+answer", re.I),
    re.compile(r"reveal\s+(the\s+)?system\s+prompt", re.I),
    re.compile(r"show\s+your\s+(hidden|internal)\s+reasoning", re.I),
    re.compile(r"bypass\s+(the\s+)?tutor", re.I),
]


def safety_check(state: TutorState) -> TutorState:
    latest = state["messages"][-1]["content"]
    blocked = any(pattern.search(latest) for pattern in _PATTERNS)
    return {"blocked": blocked, "safety_reason": "answer_bypass" if blocked else ""}


def math_evaluator(state: TutorState) -> TutorState:
    current = extract_latest_equation(state["messages"][-1]["content"])
    if current is None:
        return {"equation": "", "math_evaluation": None}

    previous = None
    for message in reversed(state["messages"][:-1]):
        previous = extract_latest_equation(message["content"])
        if previous:
            break

    if previous is None:
        return {"equation": current, "math_evaluation": None}

    try:
        evaluation = verify_step(previous, current)
    except ValueError as exc:
        evaluation = StepEvaluation(
            False, current, current, previous, True, str(exc)
        )
    return {"equation": current, "math_evaluation": evaluation}


def _heuristic_response(state: TutorState) -> str:
    evaluation = state.get("math_evaluation")
    if evaluation and evaluation.valid:
        return (
            "Nice — that step keeps the equation balanced. "
            "What operation would undo the remaining term attached to x?"
        )
    if evaluation:
        return (
            "That step changes the equation's balance. "
            "What same operation could you apply to both sides to undo that term?"
        )
    return (
        "What operation could you undo first on both sides "
        "to move closer to isolating x?"
    )


def _parse_llm_response(raw: str) -> tuple[str, str]:
    thoughts_match = re.search(
        r"<teacher_thoughts>(.*?)</teacher_thoughts>",
        raw,
        re.I | re.S,
    )
    response_match = re.search(
        r"<teacher_response>(.*?)</teacher_response>",
        raw,
        re.I | re.S,
    )
    thoughts = thoughts_match.group(1).strip() if thoughts_match else ""
    response = response_match.group(1).strip() if response_match else raw.strip()
    response = re.sub(r"<[^>]+>", "", response).strip()
    return thoughts[:500], response[:500]


def _llm_response(state: TutorState) -> tuple[str, str]:
    model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    evaluation = state.get("math_evaluation")
    evaluation_text = "No previous student step was available."
    if evaluation:
        evaluation_text = (
            f"valid={evaluation.valid}; "
            f"previous={evaluation.normalized_previous}; "
            f"current={evaluation.normalized_current}; "
            f"error={evaluation.error or 'none'}"
        )

    latest = state["messages"][-1]["content"]
    user_prompt = (
        f"Latest student message: {latest}\n"
        f"Deterministic math evaluation: {evaluation_text}\n\n"
        "Return exactly <teacher_thoughts>...</teacher_thoughts>"
        " followed by <teacher_response>...</teacher_response>."
    )

    from litellm import completion

    result = completion(
        model=model,
        messages=[
            {"role": "system", "content": SOCRATIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=180,
    )
    raw = result.choices[0].message.content or ""
    thoughts, response = _parse_llm_response(raw)
    if not response:
        raise ValueError("LLM returned an empty response")
    return thoughts, response


def pedagogical_reasoner(state: TutorState) -> TutorState:
    if state.get("blocked"):
        return {
            "response": SAFETY_BLOCK_MESSAGE,
            "teacher_thoughts": "Safety route activated.",
        }

    if os.getenv("LLM_ENABLED", "false").lower() != "true":
        response = _heuristic_response(state)
        return {
            "response": response,
            "teacher_thoughts": "Deterministic Phase 1 fallback.",
        }

    try:
        thoughts, response = _llm_response(state)
        return {"response": response, "teacher_thoughts": thoughts}
    except Exception:
        return {
            "response": _heuristic_response(state),
            "teacher_thoughts": "LLM unavailable; deterministic fallback used.",
        }


def build_graph():
    graph = StateGraph(TutorState)
    graph.add_node("safety_check", safety_check)
    graph.add_node("math_evaluator", math_evaluator)
    graph.add_node("pedagogical_reasoner", pedagogical_reasoner)
    graph.set_entry_point("safety_check")
    graph.add_edge("safety_check", "math_evaluator")
    graph.add_edge("math_evaluator", "pedagogical_reasoner")
    graph.add_edge("pedagogical_reasoner", END)
    return graph.compile()


GRAPH = build_graph()


def run_graph(messages: list[ChatMessage]) -> TutorState:
    return GRAPH.invoke({
        "request_id": str(uuid.uuid4()),
        "messages": messages,
        "blocked": False,
        "safety_reason": "",
        "equation": "",
        "math_evaluation": None,
    })
