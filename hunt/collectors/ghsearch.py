"""GitHub search collector via the authenticated `gh` CLI (public data)."""

import json
import shutil
import subprocess
from .base import observe

GH = shutil.which("gh") or "/home/asdf/.local/bin/gh"


def _gh(args):
    p = subprocess.run([GH, *args], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} -> {p.stderr.strip()[:200]}")
    return json.loads(p.stdout or "[]")


def collect(store, indicator, limit=20):
    """indicator form: gh:<search terms> — searched over repos and code."""
    _, _, terms = indicator.partition(":")
    terms = terms or indicator
    out = []
    repos = _gh(["search", "repos", terms, "--limit", str(limit),
                 "--json", "fullName,description,url,updatedAt,stargazersCount"])
    store.record("gh_query", kind="repos", query=terms, hits=len(repos))
    for r in repos:
        out.append(observe(
            "github", indicator, "repo",
            r.get("fullName"), r.get("url"),
            data={"description": r.get("description"),
                  "stars": r.get("stargazersCount"),
                  "updated": r.get("updatedAt")}))
    try:
        code = _gh(["search", "code", terms, "--limit", str(limit),
                    "--json", "repository,path,url"])
    except RuntimeError:
        code = []
    store.record("gh_query", kind="code", query=terms, hits=len(code))
    for c in code:
        out.append(observe(
            "github", indicator, "code",
            f"{c.get('repository', {}).get('nameWithOwner', '?')}:{c.get('path')}",
            c.get("url"),
            data={"path": c.get("path"),
                  "repo": c.get('repository', {}).get('nameWithOwner')}))
    return out
