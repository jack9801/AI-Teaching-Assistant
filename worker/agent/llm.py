from __future__ import annotations
import os
from typing import Any
from litellm import completion
from .prompts import SOCRATIC_SYSTEM_PROMPT

def generate(messages: list[dict[str,str]]) -> str | None:
    if os.getenv("LLM_ENABLED", "false").lower() != "true":
        return None
    model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    result: Any = completion(
        model=model,
        messages=[{"role":"system","content":SOCRATIC_SYSTEM_PROMPT}, *messages],
        temperature=0.2,
        max_tokens=180,
    )
    return str(result.choices[0].message.content).strip()
