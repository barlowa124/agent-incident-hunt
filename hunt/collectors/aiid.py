"""AI Incident Database collector.

The GraphQL API requires login for the `incidents` query (bot mitigation,
observed 2026-10-30). The public paths used here instead:

- sitemap-index.xml -> sitemap-N.xml : enumerate every /cite/<id> URL
- /page-data/cite/<id>/page-data.json : the Gatsby build's structured
  incident record (title, date, entities, descriptions, linked reports)

Both are public, unauthenticated, and sitemap-driven collection respects
the site's own crawl surface.
"""

import re
import xml.etree.ElementTree as ET
from .base import observe, fetch_json

BASE = "https://incidentdatabase.ai"
UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 "
      "Firefox/128.0")


def _sitemap_ids(store):
    meta = store.fetch(f"{BASE}/sitemap-index.xml", "aiid", ua=UA)
    idx = ET.fromstring(store.get(meta["sha256"]))
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    ids = set()
    for loc in idx.findall(".//s:loc", ns):
        m = store.fetch(loc.text, "aiid", ua=UA)
        root = ET.fromstring(store.get(m["sha256"]))
        for u in root.findall(".//s:loc", ns):
            mm = re.search(r"/cite/(\d+)", u.text or "")
            if mm:
                ids.add(int(mm.group(1)))
    return sorted(ids)


def incident(store, incident_id):
    url = f"{BASE}/page-data/cite/{incident_id}/page-data.json"
    data, meta = fetch_json(store, url, "aiid", ua=UA)
    d = data["result"]["data"]
    inc = d.get("incident") or {}
    reports = [
        {"title": r.get("title"), "url": r.get("url"),
         "date_published": r.get("date_published"),
         "source_domain": r.get("source_domain"),
         "text_len": len(r.get("text") or "")}
        for r in d["allMongodbAiidprodReports"]["nodes"]
    ]
    return observe(
        "aiid", f"incident_id:{incident_id}", "incident",
        inc.get("title"), f"{BASE}/cite/{incident_id}/",
        evidence=meta["sha256"],
        data={
            "incident_id": incident_id,
            "date": inc.get("date"),
            "description": inc.get("description"),
            "editor_notes": inc.get("editor_notes"),
            "alleged_deployer": inc.get("Alleged_deployer_of_AI_system"),
            "alleged_developer": inc.get("Alleged_developer_of_AI_system"),
            "alleged_harmed": inc.get("Alleged_harmed_or_nearly_harmed_parties"),
            "implicated_systems": inc.get("implicated_systems"),
            "reports": reports,
            "reports_full": [
                {"title": r.get("title"), "url": r.get("url"),
                 "text": r.get("text")}
                for r in d["allMongodbAiidprodReports"]["nodes"]
            ],
        })


def search(store, keyword, limit=20, max_scan=200):
    """Substring match over cite page-data records, newest first (incident
    IDs are issued in submission order). Bounded to the most recent
    `max_scan` incidents because AIID exposes no public full-text endpoint
    without login; the bound is documented in README limits."""
    hits = []
    for iid in reversed(_sitemap_ids(store)[-max_scan:]):
        try:
            o = incident(store, iid)
        except Exception:
            continue
        if keyword.lower() in json_blob(o):
            hits.append(o)
        if len(hits) >= limit:
            break
    return hits


def json_blob(obs):
    d = obs["data"]
    parts = [obs["title"] or "", d.get("description") or "",
             d.get("editor_notes") or ""]
    for k in ("alleged_deployer", "alleged_developer", "alleged_harmed",
              "implicated_systems"):
        parts += [x for x in (d.get(k) or []) if isinstance(x, str)]
    return " ".join(parts).lower()


def collect(store, indicator):
    """indicator forms: incident_id:1784, keyword:agent"""
    kind, _, val = indicator.partition(":")
    if kind == "incident_id":
        return [incident(store, int(val))]
    if kind == "keyword":
        return search(store, val)
    return []
