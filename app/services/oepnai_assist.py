import os
import json
from typing import List, Dict, Any

from openai import OpenAI


OPENAI_MODEL = os.getenv("DOORKS_OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_openai_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Calls OpenAI and returns parsed JSON.
    If parsing fails, returns {} (caller adds fallbacks).
    """
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        txt = resp.choices[0].message.content or "{}"
        return json.loads(txt)
    except Exception:
        return {}

