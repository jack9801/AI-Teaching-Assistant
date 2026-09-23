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
    if not _ALLOWED.fullmatch(raw):
        raise ValueError("Equation contains unsupported characters")
    if raw.count("=") != 1:
        raise ValueError("Expected exactly one '=' sign")
    left, right = (part.strip() for part in raw.split("=", 1))
    if not left or not right:
        raise ValueError("Both sides of the equation are required")
    x = sp.Symbol("x")
    try:
        lhs = sp.sympify(left, locals={"x": x})
        rhs = sp.sympify(right, locals={"x": x})
    except (sp.SympifyError, TypeError, ValueError) as exc:
        raise ValueError("Equation could not be parsed") from exc
    if not (lhs.is_real is not False and rhs.is_real is not False):
        raise ValueError("Equation contains unsupported symbolic values")
    return sp.Eq(lhs, rhs, evaluate=False)


def _equivalent_linear_equations(a: sp.Equality, b: sp.Equality) -> bool:
    x = sp.Symbol("x")
    da = sp.Poly(sp.expand(a.lhs - a.rhs), x)
    db = sp.Poly(sp.expand(b.lhs - b.rhs), x)
    if da.degree() < 0 or db.degree() < 0:
        return True
    if da.degree() > 1 or db.degree() > 1:
        return False
    a_coeffs = da.all_coeffs()
    b_coeffs = db.all_coeffs()
    if len(a_coeffs) != len(b_coeffs):
        return False
    first = next((i for i, value in enumerate(a_coeffs) if value != 0), None)
    if first is None:
        return all(value == 0 for value in b_coeffs)
    ratio = sp.simplify(b_coeffs[first] / a_coeffs[first])
    return ratio != 0 and all(
        sp.simplify(b_coeffs[i] - ratio * a_coeffs[i]) == 0
        for i in range(len(a_coeffs))
    )


def verify_step(previous: str, current: str) -> StepEvaluation:
    prev_eq = _parse_equation(previous)
    curr_eq = _parse_equation(current)
    x = sp.Symbol("x")

    prev_solution = sp.solve(prev_eq, x)
    curr_solution = sp.solve(curr_eq, x)

    valid = bool(
        prev_solution == curr_solution
        and _equivalent_linear_equations(prev_eq, curr_eq)
    )

    return StepEvaluation(
        valid=valid,
        equation=current,
        normalized_current=f"{sp.expand(curr_eq.lhs)} = {sp.expand(curr_eq.rhs)}",
        normalized_previous=f"{sp.expand(prev_eq.lhs)} = {sp.expand(prev_eq.rhs)}",
        changed=not (
            sp.simplify(prev_eq.lhs - curr_eq.lhs) == 0
            and sp.simplify(prev_eq.rhs - curr_eq.rhs) == 0
        ),
        error=None if valid else "The new equation is not algebraically equivalent to the previous equation.",
    )


_EQUATION = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"([+-]?(?:\d+(?:\.\d+)?\s*)?x(?:\s*[+-]\s*\d+(?:\.\d+)?)?|[+-]?\d+(?:\.\d+)?)"
    r"\s*=\s*"
    r"([+-]?(?:\d+(?:\.\d+)?\s*)?x(?:\s*[+-]\s*\d+(?:\.\d+)?)?|[+-]?\d+(?:\.\d+)?)"
    r"(?![A-Za-z0-9_])",
    re.I,
)


def extract_latest_equation(message: str) -> str | None:
    matches = list(_EQUATION.finditer(message))
    if not matches:
        return None
    return matches[-1].group(0).strip()
