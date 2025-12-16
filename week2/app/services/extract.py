from __future__ import annotations

import json
import re

from dotenv import load_dotenv
from ollama import chat

load_dotenv()

BULLET_PREFIX_PATTERN = re.compile(r"^\s*([-*•]|\d+\.)\s+")
KEYWORD_PREFIXES = (
    "todo:",
    "action:",
    "next:",
)


def _is_action_line(line: str) -> bool:
    stripped = line.strip().lower()
    if not stripped:
        return False
    if BULLET_PREFIX_PATTERN.match(stripped):
        return True
    if any(stripped.startswith(prefix) for prefix in KEYWORD_PREFIXES):
        return True
    if "[ ]" in stripped or "[todo]" in stripped:
        return True
    return False


def extract_action_items(text: str) -> list[str]:
    lines = text.splitlines()
    extracted: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if _is_action_line(line):
            cleaned = BULLET_PREFIX_PATTERN.sub("", line)
            cleaned = cleaned.strip()
            # Trim common checkbox markers
            cleaned = cleaned.removeprefix("[ ]").strip()
            cleaned = cleaned.removeprefix("[todo]").strip()
            extracted.append(cleaned)
    # Fallback: if nothing matched, heuristically split into sentences and pick imperative-like ones
    if not extracted:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            if _looks_imperative(s):
                extracted.append(s)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in extracted:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(item)
    return unique


def extract_action_items_llm(text: str, *, model: str = "llama3.1:8b") -> list[str]:
    """
    LLM-powered alternative to `extract_action_items()` using Ollama structured outputs.
    Returns a JSON-derived list of action item strings.
    """
    text = (text or "").strip()
    if not text:
        return []

    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
        "required": ["items"],
    }

    try:
        response = chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract action items from free-form notes. "
                        "Return only concise, de-duplicated action items."
                    ),
                },
                {"role": "user", "content": text},
            ],
            format=schema,
        )
        content = str(response.get("message", {}).get("content", "")).strip()
        parsed = json.loads(content) if content else {}
        raw_items = parsed.get("items", [])
        if not isinstance(raw_items, list):
            return extract_action_items(text)

        cleaned: list[str] = []
        seen: set[str] = set()
        for item in raw_items:
            if not isinstance(item, str):
                continue
            s = item.strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(s)
        return cleaned
    except Exception:
        # Keep the app usable even if Ollama isn't running or returns invalid JSON.
        return extract_action_items(text)


def _looks_imperative(sentence: str) -> bool:
    words = re.findall(r"[A-Za-z']+", sentence)
    if not words:
        return False
    first = words[0]
    # Crude heuristic: treat these as imperative starters
    imperative_starters = {
        "add",
        "create",
        "implement",
        "fix",
        "update",
        "write",
        "check",
        "verify",
        "refactor",
        "document",
        "design",
        "investigate",
    }
    return first.lower() in imperative_starters
