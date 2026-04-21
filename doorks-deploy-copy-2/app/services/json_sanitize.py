from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any


def _to_builtin_scalar(x: Any) -> Any:
    # numpy/pandas scalars often have .item()
    try:
        if hasattr(x, "item"):
            return x.item()
    except Exception:
        pass
    return x


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively converts objects into JSON-safe types:
    - NaN/Inf -> None
    - numpy/pandas scalars -> python scalars
    - datetime/date -> ISO string
    """
    obj = _to_builtin_scalar(obj)

    if obj is None:
        return None

    # primitives
    if isinstance(obj, (str, bool, int)):
        return obj

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # dict
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    # list/tuple/set
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(v) for v in obj]

    # bytes
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8", errors="replace")
        except Exception:
            return str(obj)

    # fallback to string
    try:
        return str(obj)
    except Exception:
        return None
