# agent-incident-hunt

Passive OSINT collection on AI-agent incidents. Five public-source
collectors feed one hash-chained evidence store. An indicator pivot
command links observations across sources. Triage follows a rubric with
an LLM-assisted rationale step. Five case files document real incidents.
A localhost decoy service distinguishes agent traffic from ordinary
bots and browsers.

## Layout

| Path | Contents |
|---|---|
| `hunt/` | evidence store, collectors, pivot, triage, LLM client |
| `indicators/indicators.yaml` | versioned indicator file with provenance |
| `cases/` | five case files from real public sources |
| `decoy/` | decoy web service, detection rules, labeled traffic eval |
| `docs/` | methodology and the triage rubric |
| `evidence/` | content-addressed captures plus `chain.jsonl` |
| `results/` | pivot outputs, triage records, decoy eval |
| `tests/` | pytest suite for the store and the detector |

## Sources and access

All collection is passive over public sources with no login bypass: AIID
sitemaps and page-data JSON, the urlscan.io public search API, Wayback
CDX, `gh search`, and HN Algolia. The AIID GraphQL API requires login for
the `incidents` query as of 2026-10-30, so <!-- deslop-disable-line magic-number --> the collector walks the public
sitemap and per-page `page-data.json` instead. `docs/methodology.md`
covers the paths used and the rate-limit stance.

## Reproduce

```sh
python3 -m pytest tests/ -q          # 12 unit tests, no network

# capture + chain
python3 -m hunt.pivot --indicator incident_id:1784
python3 -m hunt.pivot --indicator domain:alignment.openai.com
python3 -m hunt.pivot --file indicators/indicators.yaml --id IND-005
python3 -m hunt.evidence evidence    # replay chain, re-hash artifacts

# triage (needs local ollama with qwen3-vl:4b)
python3 -c "from hunt.evidence import EvidenceStore; \
  from hunt.triage import triage_file; \
  triage_file(EvidenceStore('evidence'), 'results/pivots/<file>.jsonl')"

# decoy eval (needs the server running + playwright + system chromium)
python3 decoy/server.py --port 8787 &
python3 decoy/eval.py --rounds 3 --with-llm
```

## Measured results

- Evidence chain: 163 chained entries, and `python3 -m hunt.evidence
  evidence` re-hashes every artifact clean. An earlier write race forked
  the chain. `scripts/rebuild_chain.py` re-chained the same captures and
  `evidence/chain.forked.jsonl` keeps the broken original.
- Case files: five, under `cases/`, each bound to captured report text.
- Keyword sweep: `keyword:agent` over the newest 200 AIID records
  returned 19 incidents and 51 HN observations.
- Decoy eval, 15 runs in `results/decoy_eval.json`: <!-- deslop-disable-line magic-number --> bot classes and the
  browser class were identified 3/3 each. The scripted agent was caught
  3/3 through the hidden-canary signal. The LLM-steered agent was caught
  2/3. The third run stalled on model latency and looked like a probe.
  Labeled traffic is lab data, generated locally.

## Decoy service

`decoy/server.py` serves a page with visible links and a `display:none`
canary link. A JS endpoint records whether script executed, and a
robots.txt discloses a second canary. `decoy/detect.py` classifies a
request log into a browser class, an agent class, a bot class, or
unknown, using only observable signals. `decoy/traffic.py` generates the
labeled classes. Two are bots: a single-probe fetch and a robots-reading
curl client. Two are agents: a scripted DOM parser and an LLM-steered
client on local ollama. The fifth is real headless Chromium standing in
for the browser class. The confusion matrix lives in
`results/decoy_eval.json`.

## Limits

- No live agent was ever directed at a third-party system. Decoy traffic
  is lab-generated on localhost and labeled as such.
- AIID keyword search scans the newest 200 cite records rather than
  the full catalog, since no public full-text endpoint exists without
  login.
- The hash chain detects tampering and mid-chain deletion. It cannot
  detect truncation of its own tail, and
  `test_tail_truncation_is_undetectable` pins that limit.
- The browser class is a headless Chromium stand-in. A human browser is
  indistinguishable at this fidelity and no human traffic was generated.
- The LLM step is a local 4B model and its scores are recorded as
  rationale, not ground truth. The heuristic scores are the reproducible
  half of triage.
- Case-file inferences are marked and remain hypotheses.
