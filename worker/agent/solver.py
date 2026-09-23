from __future__ import annotations
import re
from dataclasses import dataclass
import sympy as sp

@dataclass(frozen=True)
class StepEvaluation:
    valid: bool
    equation: str
    normalized_current: str
    normalized_previous: str
    changed: bool
    error: str | None

_ALLOWED = re.compile(r"^[0-9a-zA-ZxX+\-*/=().\s]+$")

def _parse_equation(text: str) -> sp.Equality:
    raw = text.strip().replace("X", "x")
    if not _ALLOWED.fullmatch(raw) or raw.count("=") != 1:
        raise ValueError("Expected a supported equation with exactly one '=' sign")
    left, right = (part.strip() for part in raw.split("=", 1))
    if not left or not right:
        raise ValueError("Both sides of the equation are required")
    x = sp.Symbol("x")
    return sp.Eq(sp.sympify(left, locals={"x": x}), sp.sympify(right, locals={"x": x}), evaluate=False)

def verify_step(previous: str, current: str) -> StepEvaluation:
    prev_eq, curr_eq = _parse_equation(previous), _parse_equation(current)
    x = sp.Symbol("x")
    same_solution = sp.solve(prev_eq, x) == sp.solve(curr_eq, x)
    prev_diff = sp.expand(prev_eq.lhs - prev_eq.rhs)
    curr_diff = sp.expand(curr_eq.lhs - curr_eq.rhs)
    equivalent = sp.simplify(prev_diff - curr_diff) == 0 or sp.simplify(prev_diff + curr_diff) == 0
    valid = bool(same_solution and equivalent)
    return StepEvaluation(valid, current, f"{sp.expand(curr_eq.lhs)} = {sp.expand(curr_eq.rhs)}", f"{sp.expand(prev_eq.lhs)} = {sp.expand(prev_eq.rhs)}", True, None if valid else "The new equation is not algebraically equivalent to the previous equation.")

def extract_latest_equation(message: str) -> str | None:
    matches = re.findall(r"[0-9a-zA-ZxX+\-*/().\s]+=[0-9a-zA-ZxX+\-*/().\s]+", message)
    for candidate in matches:
        candidate = candidate.strip()
        if any(ch.isdigit() for ch in candidate):
            return candidate
    return None
