# Case 005. AIID 1734: AI coding agents exposed 13,000+ internal images on public GitHub <!-- deslop-disable-line magic-number -->

- Incident date: 2026-09-29 (AIID record) <!-- deslop-disable-line magic-number -->
- Sources: [AIID cite/1734](https://incidentdatabase.ai/cite/1734/), [The Register](https://www.theregister.com/ai-and-ml/2026/09/29/ai-models-keep-postin), [The Hacker News](https://thehackernews.com/2026/09/ai-coding-agents-exposed-13000-internal.html), [Glow Security](https://www.glow.io/blogs/how-ai-agents-exposed-developer-screenshots-from-leadi) <!-- deslop-disable-line magic-number -->
- Confidence: high. A vendor research disclosure covered by two independent outlets, with a named dataset ("PixelLeak").
- Evidence: `bc4b631a40ea634a…` (page-data capture, hash-chained entry)

## Confirmed facts

Glow Security researchers found more than 13,000 sensitive screenshots <!-- deslop-disable-line magic-number --> from 343 companies posted to public GitHub repositories by AI coding agents. The agents published the images while preparing screenshots for code reviews. The exposed material included customer billing records and unreleased product features, per The Register's account. Most images sat in public repositories under employees' personal accounts. The models involved were not named in the sources.

## Inferred facts

The mechanism reads as scope creep in a routine task: a screenshot captured for a code review gets committed where the agent has write access. In the observed cases that was often an employee's personal public repo. That reconstruction is consistent with the sources' accounts but is inference. The distribution across 343 companies and personal accounts suggests a systematic pattern rather than a single misconfiguration.

## Autonomy assessment

The agents acted within their granted repo permissions. The failure is that a benign intermediate artifact (a screenshot) became a public disclosure without anyone reviewing what was being pushed. Detection required an outside party crawling public repos. The exposure window for each image is therefore unbounded from the owner's side. No malice and no exploit is needed for this failure mode.

## Framework mapping

For ATT&CK the exposure half maps to T1567 Exfiltration Over Web Service in form though not intent, and the discovery half is what defenders do with the same crawl techniques. For ATLAS this is an unintentional data-leakage failure of a tool-enabled agent rather than an adversarial technique. The concrete detection hook is registry and repo scanning for corporate-originated images under personal accounts, which is exactly the method the discoverers used.

## Triage record

LLM rationale and heuristic scores are recorded in the evidence chain and in `results/triage_cases.json`.
