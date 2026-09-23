from __future__ import annotations
import re, uuid
from typing import Literal, TypedDict
from langgraph.graph import END, StateGraph
from .prompts import SAFETY_BLOCK_MESSAGE
from .solver import StepEvaluation, extract_latest_equation, verify_step
from .llm import generate

class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str
class TutorState(TypedDict, total=False):
    request_id: str; messages: list[ChatMessage]; blocked: bool; safety_reason: str; equation: str; math_evaluation: StepEvaluation | None; response: str; teacher_thoughts: str
_PATTERNS=[re.compile(r"ignore\s+(all\s+)?previous\s+instructions",re.I),re.compile(r"(just|only)\s+(give|tell)\s+(me\s+)?(the\s+)?answer",re.I),re.compile(r"reveal\s+(the\s+)?system\s+prompt",re.I),re.compile(r"show\s+your\s+(hidden|internal)\s+reasoning",re.I)]

def safety_check(state:TutorState)->TutorState:
    latest=state["messages"][-1]["content"]; blocked=any(p.search(latest) for p in _PATTERNS)
    return {"blocked":blocked,"safety_reason":"answer_bypass" if blocked else ""}

def math_evaluator(state:TutorState)->TutorState:
    current=extract_latest_equation(state["messages"][-1]["content"])
    if current is None:return {"equation":"","math_evaluation":None}
    previous=None
    for m in reversed(state["messages"][:-1]):
        previous=extract_latest_equation(m["content"])
        if previous:break
    if previous is None:return {"equation":current,"math_evaluation":None}
    try: ev=verify_step(previous,current)
    except ValueError as exc: ev=StepEvaluation(False,current,current,previous,True,str(exc))
    return {"equation":current,"math_evaluation":ev}

def pedagogical_reasoner(state:TutorState)->TutorState:
    if state.get("blocked"): response=SAFETY_BLOCK_MESSAGE
    else:
        ev=state.get("math_evaluation")
        fallback=("Nice — that step keeps the equation balanced. What operation would undo the remaining term attached to x?" if ev and ev.valid else "That step changes the equation's balance. What same operation could you apply to both sides to undo that term?" if ev else "What operation could you undo first on both sides to move closer to isolating x?")
        try: response=generate([{"role":m["role"],"content":m["content"]} for m in state["messages"]]) or fallback
        except Exception: response=fallback
    return {"response":response,"teacher_thoughts":"Internal reasoning withheld."}

def build_graph():
    g=StateGraph(TutorState);g.add_node("safety_check",safety_check);g.add_node("math_evaluator",math_evaluator);g.add_node("pedagogical_reasoner",pedagogical_reasoner);g.set_entry_point("safety_check");g.add_edge("safety_check","math_evaluator");g.add_edge("math_evaluator","pedagogical_reasoner");g.add_edge("pedagogical_reasoner",END);return g.compile()
GRAPH=build_graph()
def run_graph(messages:list[ChatMessage])->TutorState:return GRAPH.invoke({"request_id":str(uuid.uuid4()),"messages":messages,"blocked":False,"math_evaluation":None})
