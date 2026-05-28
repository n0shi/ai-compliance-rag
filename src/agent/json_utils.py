"""Robust JSON parsing for local/cloud models."""
from __future__ import annotations
import json, re

def strip_markdown_fences(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json|JSON)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content).strip()
    return content

def parse_model_json(content: str) -> dict:
    content = strip_markdown_fences(content)
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict): return parsed[0]
        if isinstance(parsed, dict): return parsed
        raise ValueError("JSON root must be object")
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    if start < 0: raise json.JSONDecodeError("No JSON object found", content, 0)
    depth, in_str, escape = 0, False, False
    for i in range(start, len(content)):
        ch = content[i]
        if in_str:
            if escape: escape = False
            elif ch == "\\": escape = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return json.loads(content[start:i+1])
    raise json.JSONDecodeError("Could not find balanced JSON object", content, start)
