import re
import urllib.parse
from typing import List, Dict
import requests


_UA = "Mozilla/5.0 (DoorksAtlas/3.0; +localdev)"


def web_pdf_search(query: str, max_results: int = 6) -> List[Dict[str, str]]:
    """
    Lightweight PDF finder:
    - Searches DuckDuckGo HTML
    - Extracts .pdf links
    - Returns [{title,url}]
    """
    q = (query or "").strip()
    if not q:
        return []

    # Bias toward manuals/instructions
    q2 = f"{q} manual pdf"
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q2})

    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=10)
        html = r.text or ""
    except Exception:
        return []

    # Find candidate urls in results
    urls = set(re.findall(r'href="(https?://[^"]+)"', html))
    pdfs: List[Dict[str, str]] = []

    for u in urls:
        if ".pdf" not in u.lower():
            continue
        clean = u.split("&rut=")[0]
        clean = clean.replace(" ", "%20")
        title = _title_from_url(clean)
        pdfs.append({"title": title, "url": clean})
        if len(pdfs) >= max_results:
            break

    # If none, at least return a search link (still a reference)
    if not pdfs:
        pdfs.append({"title": "Search results (PDF manuals)", "url": f"https://duckduckgo.com/?q={urllib.parse.quote_plus(q2)}"})

    return pdfs


def _title_from_url(u: str) -> str:
    tail = u.split("/")[-1]
    tail = tail.split("?")[0]
    if not tail:
        return "PDF reference"
    return tail.replace("%20", " ").replace("_", " ").strip()

