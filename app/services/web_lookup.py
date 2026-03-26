from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional, Tuple

import httpx


@dataclass
class WebHit:
    title: str
    url: str
    source: str = "web"


DEFAULT_ALLOWLIST = [
    "stanleyaccess.com",
    "recorddoors.com",
    "beasensors.com",
    "dormakaba.com",
    "liftmaster.com",
    "commandaccess.com",
    "doorcontrolsusa.com",
    "addisonautomatics.com",
    "addison.com",
    "aaadm.com",
]

MANUAL_HINT_RE = re.compile(
    r"(manual|installation|service|wiring|schematic|instructions|programming|setup|user guide|operator|controller|pdf|download)",
    re.IGNORECASE,
)
PDF_RE = re.compile(r"\.pdf(\?|$)", re.IGNORECASE)

# IMPORTANT: use html.duckduckgo.com (more reliable for server-side)
DDG_HTML = "https://html.duckduckgo.com/html/?q={q}"


def _host(url: str) -> str:
    try:
        u = urllib.parse.urlparse(url)
        return (u.netloc or "").lower()
    except Exception:
        return ""


def _in_allowlist(url: str, allowlist: List[str]) -> bool:
    h = _host(url)
    return any(h == d or h.endswith("." + d) for d in allowlist)


def _looks_like_manual(title: str, url: str) -> bool:
    if PDF_RE.search(url):
        return True
    if MANUAL_HINT_RE.search(title) or MANUAL_HINT_RE.search(url):
        return True
    return False


def _clean_ddg_link(href: str) -> Optional[str]:
    if not href:
        return None
    if href.startswith("/l/"):
        parsed = urllib.parse.urlparse("https://html.duckduckgo.com" + href)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return qs["uddg"][0]
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return None


def _extract_results(html: str) -> List[Tuple[str, str]]:
    hits: List[Tuple[str, str]] = []
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        href = m.group(1)
        title_html = m.group(2)
        title = re.sub(r"<.*?>", "", title_html)
        title = re.sub(r"\s+", " ", title).strip()
        url = _clean_ddg_link(href) or ""
        if url:
            hits.append((title, url))
    return hits


def _ddg_search(query: str, timeout_s: float = 10.0) -> List[Tuple[str, str]]:
    url = DDG_HTML.format(q=urllib.parse.quote(query))
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        with httpx.Client(timeout=timeout_s, headers=headers, follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code >= 400:
                return []
            return _extract_results(r.text or "")
    except Exception:
        return []


def search_manuals(
    query: str,
    allowlist: Optional[List[str]] = None,
    max_results: int = 6,
    timeout_s: float = 10.0,
) -> List[WebHit]:
    allowlist = allowlist or DEFAULT_ALLOWLIST
    q = (query or "").strip()
    if not q:
        return []

    hits: List[WebHit] = []
    seen = set()

    # Pass A: normal query
    raw = _ddg_search(q, timeout_s=timeout_s)
    for title, link in raw:
        if link in seen:
            continue
        if not _in_allowlist(link, allowlist):
            continue
        if not _looks_like_manual(title, link):
            continue
        hits.append(WebHit(title=title, url=link, source="ddg"))
        seen.add(link)
        if len(hits) >= max_results:
            return hits

    # Pass B: targeted PDF query per domain
    for dom in allowlist:
        if len(hits) >= max_results:
            break
        site_q = f"site:{dom} (manual OR installation OR wiring OR programming) filetype:pdf {q}"
        raw2 = _ddg_search(site_q, timeout_s=timeout_s)
        for title, link in raw2:
            if link in seen:
                continue
            if not _in_allowlist(link, allowlist):
                continue
            if not (PDF_RE.search(link) or _looks_like_manual(title, link)):
                continue
            hits.append(WebHit(title=title or f"{dom} PDF", url=link, source=f"ddg-site:{dom}"))
            seen.add(link)
            if len(hits) >= max_results:
                break

    return hits


def youtube_search_link(query: str) -> str:
    q = urllib.parse.quote((query or "").strip())
    return f"https://www.youtube.com/results?search_query={q}"
