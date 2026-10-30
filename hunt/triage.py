"""Triage: rubric scoring plus an LLM-assisted rationale step.

Axes (each 0-3, docs/rubric.md):
  credibility   source standing + independent corroboration
  severity      harm class if the report is accurate
  research      novelty + mechanistic detail + pivotable indicators
    _value

Band: 7-9 escalate, 4-6 monitor, 0-3 archive.

`score_observation` runs deterministic checks; `llm_rationale` asks the
local model to assign the same axes and records both prompt and response
in the evidence chain. Disagreements are reported, not hidden.
"""

import json
import re

from . import llm
from .evidence import EvidenceStore

HIGH_STANDING = {
    "incidentdatabase.ai", "openai.com", "alignment.openai.com",
    "metr.org", "arxiv.org", "github.com", "anthropic.com",
}
SEVERITY_TERMS = {
    3: ["credential", "exfiltrat", "nonpublic", "unauthorized",
        "changed live", "deleted", "ransomware", "destructive"],
    2: ["misconfigur", "leak", "over-permissive", "bypass", "altered"],
    1: ["hallucin", "wrong answer", "minor", "cosmetic"],
}


def score_observation(obs):
    """Deterministic pre-score from observable fields only."""
    d = obs.get("data", {})
    blob = json.dumps(d).lower() + " " + (obs.get("title") or "").lower()
    cred = 0
    domains = {r.get("source_domain") for r in d.get("reports", [])}
    if obs["source"] in ("aiid",):
        cred += 2
    if any(dd in HIGH_STANDING for dd in domains if dd):
        cred += 1
    if len(d.get("reports", [])) >= 2:
        cred += 1
    sev = 0
    for level, terms in sorted(SEVERITY_TERMS.items(), reverse=True):
        if any(t in blob for t in terms):
            sev = level
            break
    research = 0
    if d.get("reports"):
        research += 1
    if any(len(r.get("text") or "") > 2000 for r in d.get("reports_full", [])):
        research += 1
    if d.get("implicated_systems"):
        research += 1
    return {"credibility": min(3, cred), "severity": sev,
            "research_value": min(3, research)}


def band(score):
    t = score["credibility"] + score["severity"] + score["research_value"]
    return ("escalate" if t >= 7 else "monitor" if t >= 4 else "archive",
            t)


PROMPT = """You are triaging an OSINT observation about an AI incident.
Score each axis 0-3 and justify in one sentence each.

credibility: source standing and independent corroboration
severity: worst plausible harm if the report is accurate
research_value: novelty, mechanistic detail, and pivotable indicators

Observation:
title: {title}
source: {source}
description: {description}
reports: {reports}

Reply with JSON only: {{"credibility": n, "severity": n,
"research_value": n, "rationale": "..."}}"""


def llm_rationale(store: EvidenceStore, obs, model=llm.MODEL):
    d = obs.get("data", {})
    prompt = PROMPT.format(
        title=obs.get("title"),
        source=obs.get("source"),
        description=(d.get("description") or "")[:2000],
        reports="; ".join(r.get("title", "") for r in d.get("reports", []))[:500],
    )
    text = llm.generate(prompt, model=model, store=store,
                        purpose=f"triage {obs.get('indicator')}")
    m = re.search(r"\{[^{}]*\}", text, re.S)
    try:
        parsed = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        parsed = {}
    rec = {"llm": parsed, "heuristic": score_observation(obs)}
    store.record("triage", indicator=obs.get("indicator"),
                 url=obs.get("url"), **rec)
    return rec


def triage_file(store, path, model=llm.MODEL):
    """Triage every observation in a pivot .jsonl; returns records."""
    recs = []
    with open(path) as f:
        for line in f:
            if line.strip():
                obs = json.loads(line)
                recs.append({"observation": obs,
                             "triage": llm_rationale(store, obs, model)})
    return recs
