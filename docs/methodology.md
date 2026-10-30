# Methodology

## Collection

Collection is passive and limited to public sources. Five collectors run
through one evidence store so every observation carries its raw capture.

| Source | Access path | Login needed |
|---|---|---|
| AI Incident Database | sitemap XML plus Gatsby page-data JSON per cite page | No |
| urlscan.io | public search API | No |
| Internet Archive | CDX search API plus snapshot fetches | No |
| GitHub | `gh search` CLI on the authenticated account | Account only |
| Hacker News | Algolia search API | No |

The AIID GraphQL endpoint answers but returns `API_LOGIN_REQUIRED` for
the `incidents` query since bot-traffic mitigation, observed 2026-10-30. <!-- deslop-disable-line magic-number -->
The collector therefore walks the public sitemap and the per-page
`page-data.json` the site itself ships to browsers. A keyword search is
bounded to the newest 200 cite pages so it does not crawl the full
catalog. The bound is a documented limit, not an oversight.

Rate limits: collectors are single-threaded with no parallelism and the
bounded scan counts keep request volume small. AIID serves no
robots.txt. The paths used are the ones the site
publishes for crawlers (sitemap) and browsers (page-data).

## Evidence handling

Every fetch lands in `evidence/store/<sha256>.bin` with a
`<sha256>.meta.json` recording URL and source plus retrieval time and an archive URL
where one exists. A hash-chained `chain.jsonl` logs each capture as
well as non-fetch events like pivots and triage and LLM prompts.
`python3 -m hunt.evidence evidence` replays the chain and re-hashes every
artifact. The test suite covers corruption and mid-chain deletion.
Tail truncation is undetectable without an external anchor, and
`test_tail_truncation_is_undetectable` pins that limit.

## Pivoting

`python3 -m hunt.pivot --indicator <type:value>` routes one indicator to
the relevant collectors and writes a linked observation file under
`results/pivots/`. Indicator types live in the versioned
`indicators/indicators.yaml`, which carries provenance per entry.

## Triage

`docs/rubric.md` defines the three-axis rubric. `hunt/triage.py` runs a
deterministic pass from observable fields and an LLM pass against a local
ollama model. Both land in the evidence chain. Disagreements are kept.

## Case files

Observations that escalate get a case file under `cases/`. Each file
separates confirmed from inferred facts, gives an autonomy assessment
plus a framework mapping. It records the evidence hashes each claim
binds to. Personal data of private individuals is redacted where
sources name them.
