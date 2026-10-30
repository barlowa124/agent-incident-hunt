"""urlscan.io public search collector. The search API answers without a key
at low rate limits; submissions would need one and are out of scope."""

from urllib.parse import quote
from .base import observe, fetch_json

API = "https://urlscan.io/api/v1/search/"


def collect(store, indicator):
    """indicator forms: domain:example.com, ip:1.2.3.4, url:<page.url>,
    hash:<sha256 of a file urlscan saw>, any raw urlscan query."""
    kind, _, val = indicator.partition(":")
    q = {
        "domain": f"domain:{val}",
        "ip": f"ip:{val}",
        "url": f'page.url:"{val}"',
        "hash": f"hash:{val}",
    }.get(kind, indicator)
    data, meta = fetch_json(store, f"{API}?q={quote(q)}&size=50", "urlscan")
    out = []
    for r in data.get("results", []):
        task, page = r.get("task", {}), r.get("page", {})
        out.append(observe(
            "urlscan", indicator, "scan",
            f"{page.get('url', '?')} via {r.get('submitter', {}).get('country', '?')}",
            r.get("result") or task.get("reportURL"),
            evidence=meta["sha256"],
            data={
                "scan_time": task.get("time"),
                "page_url": page.get("url"),
                "ip": page.get("ip"),
                "asn": page.get("asnname"),
                "country": page.get("country"),
                "server": page.get("server"),
                "verdicts": r.get("verdicts", {}).get("overall", {}),
            }))
    return out
