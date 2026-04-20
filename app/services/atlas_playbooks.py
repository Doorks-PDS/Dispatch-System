from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# These are intentionally written as "teach-style" rules:
# - short, searchable, and actionable
# - include "if/then" triggers
# - include safety patterns that matter in the field
SEED_RULES: List[Dict[str, Any]] = [
    {
        "title": "Always isolate mechanical vs operator",
        "tags": ["troubleshooting", "operator", "process"],
        "rule": (
            "If an operator is struggling / stalling / reversing: FIRST isolate mechanical vs operator.\n"
            "Test: disconnect operator (or release clutch/chain) and move door by hand.\n"
            "- If door binds by hand: fix guides/rollers/hinges/top fixtures/floor issues BEFORE touching controller settings.\n"
            "- If door is smooth by hand: then troubleshoot operator power, clutch, gearbox, limits, sensors, and control logic."
        ),
    },
    {
        "title": "RSD stuck or hard to move: common mechanical checks",
        "tags": ["rsd", "rolling steel", "mechanical"],
        "rule": (
            "If rolling steel door is stuck / jerky / loud:\n"
            "1) Check guides for crush/bow, seized endlocks, or curtain rubbing.\n"
            "2) Check barrel alignment + headplates; look for shifted barrel or worn bearings.\n"
            "3) Confirm bottom bar not caught on floor stop/anchor or safety edge cable snag.\n"
            "4) If operator drives but curtain doesn't: inspect drive coupling/keys/set screws/sprocket and clutch."
        ),
    },
    {
        "title": "Rolling steel spring safety",
        "tags": ["rsd", "rolling steel", "safety"],
        "rule": (
            "Safety rule: Rolling steel torsion springs store extreme energy.\n"
            "Use correct winding bars/tools, clamp/secure curtain, keep body out of winding path, and never loosen set screws without a controlled plan."
        ),
    },
    {
        "title": "Storefront door dragging lead edge",
        "tags": ["storefront", "hinge", "alignment"],
        "rule": (
            "If storefront door drags at LEAD edge: suspect door sag or pivot/arm misalignment.\n"
            "Checks: pivot set screws/threshold pivot, top pivot/spindle wear, closer arm play, loose top patch screws, frame sag.\n"
            "Fix path: support door weight, tighten/restore pivots, correct reveal, then adjust closer sweep/latch AFTER alignment."
        ),
    },
    {
        "title": "Herculite / patch hardware safety",
        "tags": ["glass", "herculite", "patch", "safety"],
        "rule": (
            "Safety rule: When touching glass door pivots/patch hardware, support the door weight first.\n"
            "Small fastener changes can shift the glass suddenly and crack it."
        ),
    },
    {
        "title": "Door closers: sweep vs latch vs backcheck quick map",
        "tags": ["closer", "adjustment"],
        "rule": (
            "Closer tuning quick map:\n"
            "- Sweep speed controls main swing (typically ~70° to ~10-15°).\n"
            "- Latch speed controls last few degrees into latch.\n"
            "- Backcheck controls resistance near full open.\n"
            "Always make small adjustments (1/8 turn), cycle door 3-5 times, re-check."
        ),
    },
    {
        "title": "Photo eye / safety sensor false trips",
        "tags": ["safety", "sensor", "ghosting"],
        "rule": (
            "If door 'ghosts' / reverses / reopens unexpectedly: check safety inputs BEFORE changing speeds.\n"
            "Common causes: misaligned photo eyes, dirty lenses, reflective surfaces, loose sensor wiring, bad ground, or wrong NO/NC wiring."
        ),
    },
    {
        "title": "NO vs NC quick rule of thumb (dry contact inputs)",
        "tags": ["wiring", "no", "nc", "inputs"],
        "rule": (
            "Rule of thumb for dry-contact inputs:\n"
            "- Activation is commonly NO (momentary closure triggers).\n"
            "- Safety/stop circuits are commonly NC if the controller expects a supervised/fail-safe loop.\n"
            "If the input is labeled 'monitored' or 'supervised', you must match the controller's supervision method—otherwise it will fault."
        ),
    },
    {
        "title": "When NOT to order parts yet",
        "tags": ["process", "parts", "quote"],
        "rule": (
            "Do not order parts until you confirm:\n"
            "1) exact model/operator/controller revision,\n"
            "2) whether the issue reproduces with door disconnected,\n"
            "3) whether the fault is sensor-driven (safety input) vs mechanical.\n"
            "This prevents ordering boards when the real issue is binding or wiring."
        ),
    },
    {
        "title": "Operator clutch/gear slipping indicators",
        "tags": ["operator", "clutch", "gearbox"],
        "rule": (
            "If motor runs but output doesn't move (or slips):\n"
            "- Listen for rhythmic 'ratcheting' or intermittent engagement.\n"
            "- Mark shaft + sprocket/coupler with a paint marker; run door and see if marks separate.\n"
            "- Check set screws, keys/keyways, coupler spiders, chain tension, and clutch adjustment per operator type."
        ),
    },
    {
        "title": "Automatic swing: learn cycle prep checklist",
        "tags": ["automatic", "swing", "learn", "setup"],
        "rule": (
            "Before any learn cycle on automatic swing:\n"
            "1) Verify door swings freely by hand (no binding).\n"
            "2) Verify arm geometry is correct (push/pull) and operator is mounted square.\n"
            "3) Disable/clear hold-open inputs and confirm safety sensors are not permanently active.\n"
            "Then perform learn per that model's manual steps."
        ),
    },
]


def seed_rules_file(rules_file: Path) -> int:
    """
    Seeds rules.jsonl with SEED_RULES only if the file is empty.
    Returns number of rules written.
    """
    try:
        rules_file.parent.mkdir(parents=True, exist_ok=True)
        if rules_file.exists() and rules_file.stat().st_size > 0:
            return 0
    except Exception:
        # If stat fails, don't block; try seeding carefully.
        pass

    written = 0
    with rules_file.open("a", encoding="utf-8") as f:
        for r in SEED_RULES:
            rec = {
                "ts": _now_iso(),
                "title": r.get("title", "").strip(),
                "rule": r.get("rule", "").strip(),
                "tags": r.get("tags") or [],
                "seed": True,
            }
            if rec["title"] and rec["rule"]:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
    return written
