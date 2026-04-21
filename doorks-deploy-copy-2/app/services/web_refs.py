from __future__ import annotations

import re
from typing import Dict, List

from app.services.web_lookup import search_manuals, youtube_search_link

# Small curated “always good” hits (keep tight)
REFERENCE_LIBRARY: List[Dict[str, str]] = [
    {
        "match": "mc521 pro",
        "title": "Stanley MC521 Pro Slide Controller Manual (PDF)",
        "url": "https://www.addisonautomatics.com/wp-content/uploads/manuals/stanley/MC-521%20Pro%20Slide%20Controller.pdf",
    },
    {
        "match": "record 8100",
        "title": "Record 6100/8100 Installation Manual (PDF)",
        "url": "https://d3eu1jnerk19h.cloudfront.net/documents/6100-8100-Installation-Manual.pdf",
    },
    {
        "match": "bea eagle",
        "title": "BEA EAGLE Sensor Manual (PDF)",
        "url": "https://us.beasensors.com/files/uploads/2017/04/80.0311.01_20111108.pdf",
    },
]

# Domains we trust for tech docs / manuals / diagrams / spec sheets
ALLOWLIST_DOMAINS = [
    # Automatic door OEMs + sensors
    "stanleyaccess.com",
    "recorddoors.com",
    "dormakaba.com",
    "kaba.com",
    "assabloy.com",
    "besam.com",
    "geze.com",
    "tormax.com",
    "boonedit.com",
    "nabcoentrances.com",
    "ditecautomations.com",
    "niceforyou.com",
    "faacgroup.com",
    "beasensors.com",
    "hotron.com",
    "optex.com",
    "ritedsystems.com",

    # Gate / operator OEMs
    "liftmaster.com",
    "chamberlain.com",
    "controlledproducts.com",
    "niceapollogateopeners.com",
    "hysecurity.com",
    "vikingaccess.com",
    "doorking.com",
    "linearproaccess.com",
    "allstar.net",

    # Door hardware OEMs
    "allegion.com",
    "schlage.com",
    "vonduprin.com",
    "lcnglobal.com",
    "sargentlock.com",
    "corbinrusswin.com",
    "yalehome.com",
    "marksusa.com",
    "detex.com",
    "adamsrite.com",
    "dorbin.com",
    "crlaurence.com",
    "g-u.com",
    "deltana.net",
    "hingesource.com",

    # Trusted doc hubs / distributors / training libraries
    "aaadm.com",
    "addisonautomatics.com",
    "doorcontrolsusa.com",
    "accesshardware.com",
    "wesco.com",
    "trudoor.com",
    "imlss.com",
    "porvene.com",
    "cooksongroup.com",
    "clopaydoor.com",
    "seclock.com",  # corrected
    "hollon.com",
    "hagerco.com",
    "pemko.com",
    "zero-intl.com",
    "nationalguard.com",
]

# Hardware / mechanical / automatic triggers → YouTube topics
VIDEO_TRIGGERS = [
    (re.compile(r"\brsd\b|\brolling steel\b|\bcoil\b|\btension\b|\bspring\b|\bbarrel\b|\bshaft\b", re.I),
     "rolling steel door operator limit setting and safety"),
    (re.compile(r"\bsectional\b|\boverhead\b|\bgarage\b|\btorsion\b|\bdrum\b|\bcable\b", re.I),
     "commercial sectional door torsion cable drum troubleshooting"),
    (re.compile(r"\bhinge\b|\bshim\b|\bdoor dragging\b|\bsagging\b|\breveal\b|\bstrike alignment\b", re.I),
     "shim hinges to fix commercial door sagging and rubbing"),
    (re.compile(r"\bcloser\b|\blcn\b|\bvalve\b|\bsweep\b|\blatch speed\b|\bbackcheck\b|\bdelayed action\b", re.I),
     "adjust commercial door closer sweep latch backcheck delayed action"),
    (re.compile(r"\bfloor closer\b|\brixson\b|\bbts\b|\bwalk(ing)? beam\b|\bpivot\b|\bcenter hung\b", re.I),
     "floor closer walking beam pivot alignment and adjustment"),
    (re.compile(r"\bpanic\b|\bexit device\b|\bvon duprin\b|\bdetex\b|\bcvr\b|\bvertical rod\b|\brim\b", re.I),
     "exit device adjustment dogging latch retraction troubleshooting"),
    (re.compile(r"\belectric strike\b|\bmaglock\b|\bpower supply\b|\baccess control\b|\brelay\b|\bdoor contact\b", re.I),
     "access control wiring basics electric strike maglock relay"),
    (re.compile(r"\blearn cycle\b|\bfirst install sequence\b|\bfis\b|\bteach\b|\bprogram\b|\bhanding\b", re.I),
     "automatic door controller learn cycle programming first install sequence"),
    (re.compile(r"\bwiring\b|\bwire\b|\bterminal\b|\binput\b|\boutput\b|\bsensor\b|\bactivation\b", re.I),
     "wire automatic door sensor activation to controller terminals"),
    (re.compile(r"\bghost(ing)?\b|\bfalse trigger\b|\bpresence\b|\bmotion\b|\bsafety field\b", re.I),
     "automatic door sensor ghosting false activation troubleshooting"),
]

def _video_link_for_query(q: str) -> str | None:
    for rx, topic in VIDEO_TRIGGERS:
        if rx.search(q or ""):
            return youtube_search_link(topic)
    return None

def find_references_for_query(q: str, limit: int = 6) -> List[Dict[str, str]]:
    """
    Priority:
    1) curated exact hits
    2) allowlist web lookup (PDF/manual/spec bias lives in web_lookup.py)
    3) optional YouTube search link (as a fallback)
    """
    t = (q or "").lower().strip()
    hits: List[Dict[str, str]] = []

    # 1) curated first
    for r in REFERENCE_LIBRARY:
        if r["match"] in t:
            hits.append({"title": r["title"], "url": r["url"]})
            if len(hits) >= max(1, limit):
                return hits[:limit]

    # 2) controlled web lookup
    if len(hits) < limit:
        web_hits = search_manuals(q, allowlist=ALLOWLIST_DOMAINS, max_results=max(1, limit - len(hits)))
        for h in web_hits:
            hits.append({"title": h.title, "url": h.url})
            if len(hits) >= limit:
                break

    # 3) optional video search link
    v = _video_link_for_query(q)
    if v and len(hits) < limit:
        hits.append({"title": "How-to videos (YouTube search)", "url": v})

    return hits[:limit]
