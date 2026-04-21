from typing import Literal

Intent = Literal[
    "troubleshoot",
    "wiring_setup",
    "programming",
    "parts_id",
    "general"
]


def classify_intent(q: str) -> str:
    s = (q or "").lower()
    if any(k in s for k in ["wire", "terminal", "land", "tb", "input", "output", "com", "no ", "nc ", "diagram"]):
        return "wiring_setup"
    if any(k in s for k in ["program", "learn", "learn cycle", "fis", "setup", "relearn", "handheld programmer", "dip switch", "parameter"]):
        return "programming"
    if any(k in s for k in ["what is this", "identify", "model", "part number", "which closer", "which sensor"]):
        return "parts_id"
    if any(k in s for k in ["won't", "will not", "fault", "error", "code", "stuck", "ghosting", "intermittent"]):
        return "troubleshoot"
    return "general"


def requires_references(intent: str, q: str) -> bool:
    # hard rule from you:
    # "All wiring, programming, learning, or initial setup procedures always need a reference"
    return intent in ("wiring_setup", "programming")

