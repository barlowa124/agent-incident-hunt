"""Shared collector plumbing: fetch through the evidence store, emit observations."""

import json
import time


def observe(source, indicator, kind, title, url, data=None, evidence=None,
            archive_url=None):
    return {
        "source": source,
        "indicator": indicator,
        "type": kind,
        "title": title,
        "url": url,
        "archive_url": archive_url,
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_sha256": evidence,
        "data": data or {},
    }


def fetch_json(store, url, source, archive_url=None, ua=None):
    kwargs = {"ua": ua} if ua else {}
    meta = store.fetch(url, source, archive_url=archive_url, **kwargs)
    return json.loads(store.get(meta["sha256"])), meta
