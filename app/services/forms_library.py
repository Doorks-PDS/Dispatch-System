from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.services.storage import repo_data_path


@dataclass
class FormDoc:
    id: str
    title: str
    filename: str
    description: str
    tags: List[str]


FORMS: List[FormDoc] = [
    FormDoc(
        id="storefront_takeoff",
        title="Storefront Takeoff",
        filename="Storefront-Takeoff.pdf",
        description="Storefront takeoff sheet (stiles/rails, glazing, hardware, closer, frame/system).",
        tags=["storefront", "takeoff", "prl", "aluminum", "glass"],
    ),
    FormDoc(
        id="door_order_single",
        title="Door Order Sheet (Single)",
        filename="Door-Order-Sheet-Single.pdf",
        description="Single door order sheet (size, hinge prep, cutouts, undercut, channels/edges).",
        tags=["door", "order", "single", "steel", "hollow metal"],
    ),
    FormDoc(
        id="door_order_pair",
        title="Door Order Sheet (Pair)",
        filename="Door-Order-Sheet-Pair.pdf",
        description="Pair door order sheet (pair details, astragal, cutouts, net sizes, hinge prep).",
        tags=["door", "order", "pair", "steel", "hollow metal"],
    ),
    FormDoc(
        id="frame_order_single",
        title="Frame Order Sheet (Single)",
        filename="Frame-Order-Sheet-Single.pdf",
        description="Single frame order sheet (throat, jamb depth, strike prep, anchors, silencers).",
        tags=["frame", "order", "single", "hollow metal"],
    ),
    FormDoc(
        id="frame_order_pair",
        title="Frame Order Sheet (Pair)",
        filename="Frame-Order-Sheet-Pair.pdf",
        description="Pair frame order sheet (throat, jamb depth, strikes, anchors, silencers).",
        tags=["frame", "order", "pair", "hollow metal"],
    ),
]


def forms_dir(project_root: str) -> Path:
    return repo_data_path(project_root, "forms")


def list_forms(project_root: str) -> List[Dict]:
    return [
        {
            "id": f.id,
            "title": f.title,
            "description": f.description,
            "tags": f.tags,
            "download_url": f"/forms/download/{f.id}",
        }
        for f in FORMS
    ]


def get_form(form_id: str) -> Optional[FormDoc]:
    for f in FORMS:
        if f.id == form_id:
            return f
    return None


def resolve_form_path(project_root: str, form_id: str) -> Optional[Path]:
    f = get_form(form_id)
    if not f:
        return None
    p = forms_dir(project_root) / f.filename
    return p if p.exists() else None
