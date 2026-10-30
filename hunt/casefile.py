"""Assemble a case file from an AIID observation plus triage records.

Each case file lists confirmed facts (sourced), inferred facts (marked),
confidence, an autonomy assessment, an ATT&CK or ATLAS mapping, and the
evidence-store hashes every claim binds to.
"""

import argparse
import json
import time


def render(obs, triage_rec, case_id, archive_obs=None):
    d = obs["data"]
    det = triage_rec["heuristic"]
    lm = triage_rec.get("llm", {})
    b, total = _band(det)
    reports = d.get("reports", [])
    lines = [
        f"# Case {case_id}: {obs['title']}",
        "",
        f"- Source record: {obs['url']}",
        f"- Incident date: {d.get('date')}",
        f"- Confidence: {b} (rubric total {total}/9; "
        f"credibility {det['credibility']}, severity {det['severity']}, "
        f"research value {det['research_value']})",
        f"- Evidence sha256: `{obs.get('evidence_sha256')}`",
        "",
        "## Confirmed facts",
        "",
        "Facts stated by the cited sources. Each carries its report link.",
        "",
    ]
    for r in reports:
        lines.append(f"- [{r['title']}]({r['url']})"
                     + (f" ({r.get('source_domain')})" if r.get('source_domain') else ""))
    lines += [
        "",
        f"Description (as recorded by AIID): {d.get('description')}",
        "",
        "## Inferred facts",
        "",
        "Marked as inference; not stated by sources.",
        "",
        "- _None recorded._",
        "",
        "## Autonomy assessment",
        "",
        "- Actor class: AI agent with tool access (per report description).",
        "- Human oversight during the episode: see report text; the "
        "evaluation setting is described by the publisher.",
        "- Persistence/scope of action: bounded by the evaluation run.",
        "",
        "## ATT&CK / ATLAS mapping",
        "",
        "Candidate techniques for reviewer confirmation:",
        "",
        "- ATLAS AML.T0054 (LLM jailbreak/misuse surface) — tentative.",
        "- ATT&CK T1078 (Valid Accounts) if accessed systems used issued "
        "credentials — tentative.",
        "",
        "## LLM triage record",
        "",
        "```json",
        json.dumps(lm, indent=2, sort_keys=True)[:3000],
        "```",
        "",
        "## Evidence",
        "",
        f"- Pivot file observation hash: `{obs.get('evidence_sha256')}`",
        f"- Case written: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "",
    ]
    return "\n".join(lines)


def _band(score):
    t = score["credibility"] + score["severity"] + score["research_value"]
    return ("high" if t >= 7 else "medium" if t >= 4 else "low"), t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pivot", required=True)
    ap.add_argument("--incident", required=True, help="indicator string")
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--out", default="cases")
    a = ap.parse_args()
    obs = None
    with open(a.pivot) as f:
        for line in f:
            o = json.loads(line)
            if o["indicator"] == a.incident:
                obs = o
    if obs is None:
        raise SystemExit(f"{a.incident} not in {a.pivot}")
    print(json.dumps(obs["data"], indent=2)[:500])


if __name__ == "__main__":
    main()
