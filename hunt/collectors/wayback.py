"""Internet Archive Wayback CDX collector: snapshot history for a URL,
plus an optional capture of the latest snapshot body as evidence."""

from urllib.parse import quote
from .base import observe, fetch_json

CDX = "https://web.archive.org/cdx/search/cdx"
WEB = "https://web.archive.org/web"


def collect(store, indicator, limit=25):
    """indicator form: url:<target url>"""
    _, _, target = indicator.partition(":")
    target = target or indicator
    q = (f"{CDX}?url={quote(target, safe='')}&output=json&limit={limit}"
         f"&filter=statuscode:200&collapse=digest")
    data, meta = fetch_json(store, q, "wayback")
    rows = data[1:] if data else []
    out = []
    for ts, original, mimetype, status, digest, _len in [
            (r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows]:
        snap = f"{WEB}/{ts}/{original}"
        out.append(observe(
            "wayback", indicator, "snapshot",
            f"{original} @ {ts}", snap,
            evidence=meta["sha256"], archive_url=snap,
            data={"timestamp": ts, "original": original,
                  "mimetype": mimetype, "digest": digest}))
    return out


def snapshot(store, url, timestamp="latest"):
    """Capture a specific (or latest) snapshot body into the evidence store."""
    snap = f"{WEB}/{timestamp}/{url}"
    return store.fetch(snap, "wayback", archive_url=snap)
