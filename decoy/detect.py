"""Detection rules: classify a request log into agent / browser / bot / unknown.

Signals per request set (one traffic-generator run):
  beacon      POST /api/beacon -> JS executed -> browser class
  canary      GET /c/<tok> or /hidden/<tok> -> parsed DOM or robots.txt
  robots      fetched /robots.txt
  assets      fetched /static/app.js
  ua          UA string heuristics
  depth       how many distinct paths were requested

Classes:
  browser   beacon fired
  agent     canary hit without beacon (DOM parsed, no JS) and not a
            known-bot UA
  bot       robots.txt or bot UA or no link following
  unknown   none of the above decisive
"""

import argparse
import json
import re
from collections import Counter

BOT_UA = re.compile(
    r"bot\b|curl|wget|scrapy|python-requests|python-urllib|Go-http|httpie",
    re.I)
AGENT_UA = re.compile(r"agent|gpt|claude|langchain|openai", re.I)


def classify(requests):
    paths = {r["path"] for r in requests}
    uas = {r["ua"] for r in requests}
    beacon = any(r["method"] == "POST" and r["path"] == "/api/beacon"
                 for r in requests)
    canary = any("canary" in r or r["path"].startswith(("/c/", "/hidden/"))
                 for r in requests)
    robots = "/robots.txt" in paths
    assets = "/static/app.js" in paths
    ua = next(iter(uas), "")
    features = {"beacon": beacon, "canary": canary, "robots": robots,
                "assets": assets, "depth": len(paths), "ua": ua}

    if beacon:
        cls, why = "browser", "POST /api/beacon means the JS ran"
    elif canary and BOT_UA.search(ua):
        cls, why = "bot", "canary path via robots.txt, bot UA"
    elif canary:
        cls, why = "agent", "hidden link followed without JS execution"
    elif robots or BOT_UA.search(ua):
        cls, why = "bot", "robots.txt fetch or bot UA"
    elif len(paths) <= 1:
        cls, why = "bot", "single probe, no link following"
    elif assets and not beacon:
        cls, why = "bot", "fetched JS as a resource but never executed it"
    else:
        cls, why = "unknown", "links followed but no canary or beacon signal"
    return {"class": cls, "reason": why, "features": features}


def classify_log(path):
    reqs = [json.loads(l) for l in open(path) if l.strip()]
    return classify(reqs)


def evaluate(runs):
    """runs: iterable of {label, requests}. Returns a confusion matrix."""
    matrix = Counter()
    detail = []
    for run in runs:
        got = classify(run["requests"])
        matrix[(run["label"], got["class"])] += 1
        detail.append({"label": run["label"], "classified": got})
    true_labels = sorted({r["label"] for r in runs})
    classes = sorted({d["classified"]["class"] for d in detail})
    table = {l: {c: matrix[(l, c)] for c in classes} for l in true_labels}
    return {"matrix": table, "detail": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    a = ap.parse_args()
    print(json.dumps(classify_log(a.log), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
