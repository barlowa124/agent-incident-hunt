# Triage rubric

Each observation is scored on three axes, 0-3 each. The deterministic
scorer in `hunt/triage.py` and the LLM pass use the same definitions.
A total of 7-9 escalates the observation to a case file. Totals of 4-6
go to monitoring and 0-3 archive it.

| Score | Credibility | Severity | Research value |
|---|---|---|---|
| 3 | Primary-source report plus independent corroboration | Harm to systems or data: unauthorized change to live systems or bulk nonpublic access | Novel mechanism with enough detail for detection rules or pivot indicators |
| 2 | Primary-source report, or catalogued by a standing database such as AIID | Contained harm such as data exposure or a permission bypass | Some mechanism detail plus at least one pivotable indicator |
| 1 | Secondary reporting only | Quality harm such as incorrect output or degraded service | Corroborates a known pattern |
| 0 | Unsourced claim | No demonstrated harm | No actionable detail |

The deterministic score and the LLM score are reported side by side, and
case files keep both when they disagree. An observation that cannot be
reproduced from stored evidence scores 0 on credibility regardless of
the claim.
