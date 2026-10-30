# Case 004. AIID 1719: Claude Code agent deleted about 48,000 live files through Windows junctions <!-- deslop-disable-line magic-number -->

- Incident date: 2026-09-19 (AIID record) <!-- deslop-disable-line magic-number -->
- Sources: [AIID cite/1719](https://incidentdatabase.ai/cite/1719/) and [TechRadar](https://www.techradar.com/pro/security/i-broke-something-a-claude-code-ai-agent-) <!-- deslop-disable-line magic-number -->
- Confidence: low to medium. One secondary source reporting a single Reddit account, explicitly flagged as not independently verified.
- Evidence: `aed51ebb30e3ea2f…` (page-data capture, hash-chained entry)

## Confirmed facts

A developer reported tasking an AI coding assistant with repair jobs on software used to analyze stock-options data, with instructions to work on copies and leave the live tree alone. Per the TechRadar account of the Reddit post, one of eleven jobs rebuilt a test mirror containing 614 Windows directory junctions that pointed back into the live working tree. During cleanup the agent treated them as ordinary folders and followed them into the live tree. It deleted approximately 48,218 files along with <!-- deslop-disable-line magic-number --> the Git object store in 103 seconds. The AIID record itself states the account has not been independently verified.

## Inferred facts

The mechanism is a classic reparse-point footgun rather than model misbehavior in the adversarial sense. The agent presumably lacked junction-awareness in its path handling, though the report does not establish which layer failed. The "authorized scope" lesson is that file-deletion authority plus symlink or junction traversal equals effective authority over the whole reachable filesystem, which is inferable from the account but not measured in it.

## Autonomy assessment

The agent ran with filesystem write authority on the developer's machine and executed a destructive operation at machine speed, finishing in under two minutes. The oversight model was trust delegated through instructions rather than sandboxing. This case sits at the low-credibility end of the set precisely because the account is a self-report with no forensic record attached.

## Framework mapping

No ATT&CK technique applies since there is no adversary. As an ATLAS data point it documents the destructive-capability side of tool-enabled agents rather than an attack. The closest detection analog is blast-radius control. Junction-aware file operations would have stopped the traversal, and trash semantics on bulk delete would have made the damage recoverable. A rate-limit or confirmation threshold on mass deletion would have bounded it further.

## Triage record

LLM rationale and heuristic scores are recorded in the evidence chain and in `results/triage_cases.json`. The expected low credibility score versus high severity is the useful contrast in this set.
