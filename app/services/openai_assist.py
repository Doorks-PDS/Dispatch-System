from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


DEFAULT_MODEL = os.getenv("ATLAS_MODEL", "gpt-4o-mini")


def _client():
    if OpenAI is None:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_openai_json(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Strict JSON response helper.
    """
    model = model or DEFAULT_MODEL
    client = _client()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = resp.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except Exception:
        # last-resort: return wrapped
        return {"raw": content}


def call_openai_text(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
    model = model or DEFAULT_MODEL
    client = _client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()
