"""Hacker News Algolia collector (public API, no key)."""

from urllib.parse import quote
from .base import observe, fetch_json

API = "https://hn.algolia.com/api/v1"


def collect(store, indicator, limit=25):
    """indicator form: hn:<query> or keyword:<term> (falls back here for
    plain keywords)."""
    _, _, q = indicator.partition(":")
    q = q or indicator
    out = []
    for tag in ("story", "comment"):
        data, meta = fetch_json(
            store, f"{API}/search?query={quote(q)}&tags={tag}"
                   f"&hitsPerPage={limit}", "hn")
        for h in data.get("hits", []):
            oid = h.get("objectID")
            out.append(observe(
                "hn", indicator, tag,
                h.get("title") or (h.get("comment_text") or "")[:120],
                f"https://news.ycombinator.com/item?id={oid}",
                evidence=meta["sha256"],
                data={
                    "author": h.get("author"),
                    "points": h.get("points"),
                    "created_at": h.get("created_at"),
                    "story_url": h.get("url"),
                    "num_comments": h.get("num_comments"),
                }))
    return out
