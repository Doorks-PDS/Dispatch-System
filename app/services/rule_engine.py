from __future__ import annotations
import json
import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


class RuleEngine:
    """
    Simple, explainable rule system you can train like ChatGPT:
      - IF patterns match -> add recommendations, causes, diagnostics
      - Can also override symptom_class/intent when confidence is high
    """
    def __init__(self, rules_path: str = "data/atlas_memory/rules.json"):
        self.path = Path(rules_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rules: List[Dict[str, Any]] = []
        self._loaded_ts = 0

    def load(self) -> None:
        if self.path.exists():
            try:
                self.rules = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.rules = []
        else:
            self.rules = []
        self._loaded_ts = int(time.time())

    def save(self) -> None:
        self.path.write_text(json.dumps(self.rules, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_rule(self, rule: Dict[str, Any]) -> str:
        # required: name, when_any (list[str]), then (dict)
        rule = dict(rule)
        rule.setdefault("id", f"r_{int(time.time())}_{len(self.rules)+1}")
        rule.setdefault("enabled", True)
        self.rules.append(rule)
        self.save()
        return rule["id"]

    def match(self, query: str, intake: Dict[str, Any]) -> List[Dict[str, Any]]:
        q = _norm(query)
        sym = _norm(str(intake.get("symptom", "")))
        obs = _norm(str(intake.get("observed", "")))
        ctx = _norm(str(intake.get("context", "")))

        blob = " | ".join([q, sym, obs, ctx]).strip()
        hits: List[Dict[str, Any]] = []

        for r in self.rules:
            if not r.get("enabled", True):
                continue
            when_any = [ _norm(x) for x in (r.get("when_any") or []) if str(x).strip() ]
            when_all = [ _norm(x) for x in (r.get("when_all") or []) if str(x).strip() ]
            when_not = [ _norm(x) for x in (r.get("when_not") or []) if str(x).strip() ]

            if when_any and not any(k in blob for k in when_any):
                continue
            if when_all and not all(k in blob for k in when_all):
                continue
            if when_not and any(k in blob for k in when_not):
                continue

            hits.append(r)

        # simple priority: higher priority first
        hits.sort(key=lambda x: int(x.get("priority", 50)))
        return hits

    @staticmethod
    def merge_then(base: Dict[str, Any], matched_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge rule "then" blocks into a structured result.
        """
        out = dict(base)
        out.setdefault("add_causes", [])
        out.setdefault("add_diagnostics", [])
        out.setdefault("add_fix_path", [])
        out.setdefault("add_notes", [])
        out.setdefault("override_symptom_class", None)
        out.setdefault("override_intent", None)

        for r in matched_rules:
            then = r.get("then") or {}
            out["add_causes"].extend(then.get("add_causes") or [])
            out["add_diagnostics"].extend(then.get("add_diagnostics") or [])
            out["add_fix_path"].extend(then.get("add_fix_path") or [])
            out["add_notes"].extend(then.get("add_notes") or [])

            # optional overrides
            if then.get("override_symptom_class"):
                out["override_symptom_class"] = then["override_symptom_class"]
            if then.get("override_intent"):
                out["override_intent"] = then["override_intent"]

        # de-dupe while preserving order
        def dedupe(lst):
            seen = set()
            outl = []
            for x in lst:
                k = str(x).strip()
                if not k:
                    continue
                if k.lower() in seen:
                    continue
                seen.add(k.lower())
                outl.append(k)
            return outl

        out["add_causes"] = dedupe(out["add_causes"])
        out["add_diagnostics"] = dedupe(out["add_diagnostics"])
        out["add_fix_path"] = dedupe(out["add_fix_path"])
        out["add_notes"] = dedupe(out["add_notes"])
        return out

