"""
Utilities for parsing structured JSON output from LLM responses.
"""
import json
import re
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def extract_json(text: str) -> dict:
    """Extract the first JSON object found in LLM output text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract JSON block from markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find bare JSON object
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in LLM output:\n{text[:500]}")


def parse_structured_output(text: str, model_class: Type[T]) -> T:
    """Parse LLM text output into a Pydantic model."""
    data = extract_json(text)
    return model_class(**data)
