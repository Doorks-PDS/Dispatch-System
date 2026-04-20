from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.services.teach_store import TeachStore


DOOR_KEYWORDS = {
    "door", "operator", "closer", "maglock", "strike", "panic", "exit device",
    "rsd", "rolling", "roll up", "roll-up", "coil", "overhead", "gate", "sensor",
    "bea", "optex", "stanley", "record", "dormakaba", "lcn", "adams rite"
}

CATEGORY_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "auto_door_wont_open": {
        "Likely causes": [
            "Door is in OFF/HOLD/CLOSED mode or key switch disabling activation",
            "Activation device not triggering (sensor/push plate/wiring)",
            "Safety input active (presence sensor/beam/edge) preventing motion",
            "Mechanical bind/operator drive issue or controller fault",
        ],
        "Quick diagnostics": [
            "Check mode selector/key switch (AUTO vs OFF/HOLD/CLOSED).",
            "Confirm activation input changes at controller (LED/input indicator).",
            "Confirm safety inputs are not stuck active (beams aligned/clear; presence sensor not seeing obstruction).",
            "Power off and move door manually to confirm free travel (no binding).",
            "Look for fault LEDs/codes and document them.",
        ],
    },
    "auto_door_ghosting": {
        "Likely causes": [
            "Presence/safety sensor mis-aimed or seeing reflections (sun glare, shiny floors, rain)",
            "Obstruction detection from worn rollers/guides/track bind (very common)",
            "Accessory/input stuck active or intermittent wiring/loose connectors",
        ],
        "Quick diagnostics": [
            "Power off and slide door by hand; feel rough spots; inspect rollers/guides/track.",
            "Watch controller input LEDs while cycling; identify which input changes.",
            "Inspect presence sensors for reflections/glare; confirm proper mounting wedges/shims.",
            "Disconnect accessories one at a time to isolate a shorted device (trained procedure).",
        ],
    },
    "closer_leaking": {
        "Likely causes": [
            "Closer body seals failed (oil leak) causing loss of hydraulic control",
            "Door binding accelerating failure (hinges/threshold misalignment)",
        ],
        "Quick diagnostics": [
            "Confirm oil at closer body and symptom (slam / loss of control).",
            "Identify closer type (surface vs concealed) and arm style before ordering.",
            "Check binding at hinges/threshold before final tuning.",
        ],
    },
    "maglock_intermittent": {
        "Likely causes": [
            "Armature plate not flat/parallel (partial bond)",
            "Armature pivot hardware too tight (can’t self-align)",
            "Door sag/warped header shifting alignment",
            "Voltage drop under load (PSU/relay/wiring)",
        ],
        "Quick diagnostics": [
            "Verify full contact pattern (chalk test works).",
            "Confirm armature pivots freely (should ‘float’ into alignment).",
            "Measure voltage at maglock while energized and compare to PSU output.",
            "Inspect door sag and bracket type (Z&L / filler / angle).",
        ],
    },
    "rolling_door_wont_stay_up": {
        "Likely causes": [
            "Spring tension lost / door out of balance",
            "Broken spring / barrel component damage (safety risk)",
            "Curtain binding in guides causing it to drop",
        ],
        "Quick diagnostics": [
            "SAFETY: springs are hazardous—trained procedure only.",
            "Balance test: door should hold mid-travel without drifting.",
            "Inspect guides for bind and curtain for damage.",
        ],
    },
}


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


class SymptomModel:
    """
    Lightweight rule system + teach-rules overlay.

    Goal:
      - Avoid “wigs out / no idea” responses
      - Always produce a decent category + plan
      - Let techs teach rules/cases that get reused
    """

    def __init__(self, teach_store: TeachStore):
        self.teach_store = teach_store

    def classify(self, text: str) -> str:
        q = _norm(text)

        # Heavier signal patterns first
        if "ghost" in q or "opening and closing" in q or "cycling" in q:
            return "auto_door_ghosting"
        if ("automatic" in q or "operator" in q or "slider" in q or "swing" in q) and (
            "won't open" in q or "will not open" in q or "not opening" in q
        ):
            return "auto_door_wont_open"
        if "closer" in q and ("leak" in q or "oil" in q):
            return "closer_leaking"
        if "maglock" in q and ("every time" in q or "sometimes" in q or "intermitt" in q):
            return "maglock_intermittent"
        if ("roll up" in q or "roll-up" in q or "rsd" in q or "rolling" in q) and (
            "not staying up" in q or "won't stay up" in q or "falls" in q
        ):
            return "rolling_door_wont_stay_up"

        # Generic door-related?
        if any(k in q for k in DOOR_KEYWORDS):
            return "general_door"

        return "general"

    def match_taught_rules(self, text: str, max_hits: int = 3) -> List[Dict[str, Any]]:
        """
        Very simple matching:
          - If rule.trigger words all appear -> match
          - Or trigger phrase appears
        """
        q = _norm(text)
        rules = self.teach_store.get_rules(limit=500)
        hits: List[Tuple[int, Dict[str, Any]]] = []

        for r in rules:
            trig = _norm(r.get("trigger", ""))
            if not trig:
                continue

            # If user entered comma-separated keywords, require all
            parts = [p.strip() for p in trig.split(",") if p.strip()]
            if len(parts) >= 2:
                if all(p in q for p in parts):
                    hits.append((len(parts), r))
            else:
                if trig in q:
                    hits.append((1, r))

        hits.sort(key=lambda x: x[0], reverse=True)
        return [h[1] for h in hits[:max_hits]]

    def build_symptom_section(self, text: str) -> Dict[str, List[str]]:
        cat = self.classify(text)
        base = CATEGORY_TEMPLATES.get(cat, {})

        # Overlay teach rules (as extra bullets)
        taught = self.match_taught_rules(text)
        if taught:
            extra = []
            for r in taught:
                title = (r.get("title") or "").strip()
                content = (r.get("content") or "").strip()
                if content:
                    extra.append(f"{title + ': ' if title else ''}{content}")
            if extra:
                base = dict(base)  # shallow copy
                base.setdefault("Likely causes", [])
                base["Likely causes"] = base["Likely causes"] + extra[:3]

        return base if base else {}

