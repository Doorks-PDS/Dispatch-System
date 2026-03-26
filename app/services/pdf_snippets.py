from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from pypdf import PdfReader


@dataclass
class Snippet:
    title: str
    url: str
    page: int
    keyword: str
    excerpt: str
    score: float


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_\-\.]+", "_", s.strip())
    return s[:120] or "file"


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:24]


def _download_pdf(url: str, cache_dir: Path, timeout: int = 15) -> Optional[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fname = _safe_filename(_hash(url) + ".pdf")
    dest = cache_dir / fname
    if dest.exists() and dest.stat().st_size > 1000:
        return dest

    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return None
        ctype = (r.headers.get("content-type") or "").lower()
        if "pdf" not in ctype and not url.lower().endswith(".pdf"):
            # still might be pdf, but we’ll allow if content starts with PDF signature
            if not (r.content[:4] == b"%PDF"):
                return None
        dest.write_bytes(r.content)
        if dest.stat().st_size < 1000:
            return None
        return dest
    except Exception:
        return None


def _normalize_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _keywords_from_query(query: str) -> List[str]:
    q = (query or "").lower()
    # Strong domain keywords first (keeps results from drifting)
    hard = []
    if "fis" in q or "field" in q and "init" in q:
        hard += ["fis", "field initialization", "field init", "index", "operate", "status 00", "lto"]
    if "terminal" in q or "tabs" in q or "wiring" in q:
        hard += ["tb", "terminal", "input", "activation", "common", "no", "nc", "dry contact", "24v", "12v"]

    # Add query tokens (filtered)
    tokens = re.findall(r"[a-z0-9]+", q)
    tokens = [t for t in tokens if len(t) >= 3 and t not in {"the", "and", "for", "with", "door"}]

    # Deduplicate while preserving order
    seen = set()
    out = []
    for k in hard + tokens:
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out[:20]


def _score_page(text: str, keywords: List[str]) -> Tuple[float, str]:
    """
    Score a page by keyword hits. Returns (score, best_keyword).
    """
    t = (text or "").lower()
    if not t:
        return 0.0, ""

    score = 0.0
    best_kw = ""
    best_hits = 0

    for kw in keywords:
        if not kw:
            continue
        hits = t.count(kw)
        if hits > 0:
            # weight longer/stronger phrases higher
            w = 3.0 if " " in kw else 1.5
            if kw in {"fis", "index", "operate"}:
                w += 2.0
            score += hits * w
            if hits > best_hits:
                best_hits = hits
                best_kw = kw

    # Small bonus if page looks like a procedure list
    if re.search(r"\bstep\b|\bprocedure\b|\bpress\b|\bhold\b", t):
        score += 1.5

    return score, best_kw


def extract_pdf_snippets(
    web_docs: List[Dict[str, str]],
    query: str,
    max_snippets: int = 6,
    cache_dir: str = "data/uploads_runtime/pdf_cache",
    max_pdfs: int = 4,
) -> List[Dict[str, str]]:
    """
    Given a list of web_docs [{title,url}, ...], download up to max_pdfs PDFs,
    scan ALL pages, and return the best matching snippets with page numbers.
    """
    keywords = _keywords_from_query(query)
    cache_path = Path(cache_dir)

    pdfs = []
    for d in (web_docs or []):
        url = (d.get("url") or "").strip()
        title = (d.get("title") or "PDF").strip()
        if not url:
            continue
        if ".pdf" not in url.lower():
            continue
        pdfs.append((title, url))
    pdfs = pdfs[:max_pdfs]

    found: List[Snippet] = []

    for title, url in pdfs:
        local = _download_pdf(url, cache_path)
        if not local:
            continue

        try:
            reader = PdfReader(str(local))
        except Exception:
            continue

        for i, page in enumerate(reader.pages):
            try:
                raw = page.extract_text() or ""
            except Exception:
                raw = ""
            text = _normalize_text(raw)
            if not text or len(text) < 40:
                continue

            score, best_kw = _score_page(text, keywords)
            if score <= 0:
                continue

            # Build excerpt around the first hit of the best keyword (if possible)
            excerpt = text
            if best_kw:
                pos = (text.lower().find(best_kw) if best_kw in text.lower() else -1)
                if pos >= 0:
                    start = max(0, pos - 250)
                    end = min(len(text), pos + 650)
                    excerpt = text[start:end].strip()

            found.append(
                Snippet(
                    title=title,
                    url=url,
                    page=i + 1,  # 1-index for humans
                    keyword=best_kw or (keywords[0] if keywords else ""),
                    excerpt=excerpt[:950],
                    score=score,
                )
            )

    # Sort by score desc, then by page asc
    found.sort(key=lambda s: (-s.score, s.page))

    # De-dupe (same url+page)
    dedup: List[Snippet] = []
    seen = set()
    for s in found:
        key = (s.url, s.page)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(s)
        if len(dedup) >= max_snippets:
            break

    return [
        {
            "title": s.title,
            "url": s.url,
            "page": str(s.page),
            "keyword": s.keyword,
            "excerpt": s.excerpt,
        }
        for s in dedup
    ]

