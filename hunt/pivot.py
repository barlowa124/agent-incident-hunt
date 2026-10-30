"""pivot: one indicator -> observations across all applicable collectors.

Usage:
    python3 -m hunt.pivot --indicator incident_id:1784
    python3 -m hunt.pivot --indicator domain:alignment.openai.com
    python3 -m hunt.pivot --file indicators/indicators.yaml --id IND-001

Writes results/pivots/<ts>_<slug>.jsonl (one observation per line) and
appends a pivot record to the evidence chain.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from .evidence import EvidenceStore
from .collectors import aiid, urlscan, wayback, ghsearch, hn

def wayback_url(store, indicator):
    """For domain: pivots, snapshot the bare domain URL."""
    _, _, v = indicator.partition(":")
    return wayback.collect(store, f"url:https://{v}/")


# indicator prefix -> collectors to run
ROUTES = {
    "incident_id": [aiid],
    "keyword": [aiid, hn],
    "domain": [urlscan, wayback_url, hn],
    "url": [wayback, urlscan],
    "ip": [urlscan],
    "hash": [urlscan],
    "gh": [ghsearch],
    "hn": [hn],
}


def slug(s):
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:60]


def run_pivot(store, indicator, outdir="results/pivots"):
    kind = indicator.partition(":")[0]
    collectors = ROUTES.get(kind)
    if collectors is None and indicator.startswith(("domain:", "ip:")):
        collectors = [urlscan]
    if collectors is None:
        # bare keyword -> AIID + HN
        collectors = [aiid, hn]
    observations = []
    for c in collectors:
        fn = getattr(c, "collect", c)
        try:
            observations += fn(store, indicator)
        except Exception as e:
            store.record("collector_error", collector=fn.__name__,
                         indicator=indicator, error=str(e)[:200])
            print(f"  ! {fn.__name__}: {e}", file=sys.stderr)
    Path(outdir).mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = Path(outdir) / f"{ts}_{slug(indicator)}.jsonl"
    with open(out, "w") as f:
        for o in observations:
            f.write(json.dumps(o, sort_keys=True) + "\n")
    store.record("pivot", indicator=indicator,
                 observations=len(observations), out=str(out))
    return out, observations


def load_indicator(path, want_id):
    import yaml
    doc = yaml.safe_load(open(path))
    for ind in doc["indicators"]:
        if ind["id"] == want_id:
            return f"{ind['type']}:{ind['value']}"
    raise KeyError(want_id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indicator")
    ap.add_argument("--file")
    ap.add_argument("--id")
    ap.add_argument("--store", default="evidence")
    ap.add_argument("--out", default="results/pivots")
    a = ap.parse_args()
    if a.file and a.id:
        indicator = load_indicator(a.file, a.id)
    elif a.indicator:
        indicator = a.indicator
    else:
        ap.error("give --indicator or --file + --id")
    store = EvidenceStore(a.store)
    out, obs = run_pivot(store, indicator, a.out)
    print(f"{len(obs)} observations -> {out}")


if __name__ == "__main__":
    main()
