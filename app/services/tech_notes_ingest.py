from pathlib import Path
from typing import Optional, List
import pandas as pd


def _read_csv_forgiving(path: Path) -> pd.DataFrame:
    # Try utf-8 first, then latin-1 fallback
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


def _pick_notes_column(columns: List[str]) -> Optional[str]:
    """
    Pick the most likely notes column from a list of column names.
    Returns the original column name (not lowercased).
    """
    exact_priority = [
        "notes",
        "note",
        "tech_notes",
        "technician_notes",
        "comments",
        "comment",
        "job_notes",
    ]

    lowered = {str(c).lower().strip(): str(c) for c in columns}

    for key in exact_priority:
        if key in lowered:
            return lowered[key]

    # Anything containing "note"
    for c in columns:
        if "note" in str(c).lower():
            return str(c)

    return None


def _build_notes_fallback(df: pd.DataFrame) -> pd.Series:
    """
    If there's no obvious notes column, build one from common text fields,
    otherwise from all object/string columns.
    """
    common_fields = [
        "Description Of Problem",
        "Job - Work Performed",
        "Additional Repairs Needed/Recommended",
        "Material Used",
        "Work Performed",
        "Problem",
        "Resolution",
        "Notes",
        "Note",
    ]
    existing_common = [c for c in common_fields if c in df.columns]

    if existing_common:
        parts = [df[c].astype(str).fillna("") for c in existing_common]
        joined = parts[0]
        for p in parts[1:]:
            joined = joined + " | " + p
        return joined

    obj_cols = [c for c in df.columns if df[c].dtype == "object"]
    if not obj_cols:
        return pd.Series([""] * len(df))

    parts = [df[c].astype(str).fillna("") for c in obj_cols]
    joined = parts[0]
    for p in parts[1:]:
        joined = joined + " | " + p
    return joined


def load_tech_notes_df(csv_path: str) -> pd.DataFrame:
    """
    Loads technician notes CSV and guarantees there is a 'notes' column
    for AtlasSearch(text_column="notes").

    - Safe encoding load
    - Strips column whitespace
    - Auto-detects notes-like column OR builds one
    """
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"Notes CSV not found: {p}")

    df = _read_csv_forgiving(p)

    # Strip whitespace off column names (common export issue)
    df.columns = [str(c).strip() for c in df.columns]

    # Ensure we have a 'notes' column
    if "notes" not in df.columns:
        picked = _pick_notes_column(list(df.columns))
        if picked is not None:
            df["notes"] = df[picked].astype(str).fillna("")
        else:
            df["notes"] = _build_notes_fallback(df).astype(str).fillna("")
    else:
        df["notes"] = df["notes"].astype(str).fillna("")

    return df
