# Case 003. AIID 1680: Cline prompt injection led to a compromised npm publish token

- Incident date: 2026-02-17 (publish time of cline@2.3.0, 3:26 AM PT) <!-- deslop-disable-line magic-number -->
- Sources: [AIID cite/1680](https://incidentdatabase.ai/cite/1680/), [Adnan Khan writeup](https://adnanthekhan.com/posts/clinejection/), [Cline post-mortem](https://cline.bot/blog/post-mortem-unauthorized-cline-cli-npm), [GHSA-9ppg-jx86-fqw7](https://github.com/cline/cline/security/advisories/GHSA-9ppg-jx86-fqw7), [StepSecurity](https://www.stepsecurity.io/blog/cline-supply-chain-attack-detected-cline-2-3-0-), [Socket](https://socket.dev/blog/cline-cli-npm-package-compromised-via-suspected-cache-po) <!-- deslop-disable-line magic-number -->
- Confidence: high. Vendor post-mortem plus a GHSA plus two independent security-vendor detections and the researcher's own account.
- Evidence: `ce32c62aeb933939…` (page-data capture, hash-chained entry)

## Confirmed facts

An unauthorized party used a compromised npm publish token to publish cline@2.3.0 at 3:26 AM PT on February 17, 2026. The only change <!-- deslop-disable-line magic-number --> was a postinstall script running `npm install -g openclaw@latest`. The CLI binary stayed byte-identical to 2.2.3 and no malicious code shipped in the package itself. StepSecurity counts approximately 4,000 downloads <!-- deslop-disable-line magic-number --> in the roughly 8-hour exposure window before 2.4.0 replaced it. The token was revoked and OIDC provenance was adopted for publishing.

Researcher Adnan Khan reported the prompt-injection vulnerability in Cline's Claude-powered GitHub issue-triage workflow and confirmed it on a mirror repository. His writeup says a different actor found the PoC on his test repository and used it against the real Cline repo. The attacker obtained the publication credentials through a GitHub Actions cache-poisoning path. Cline's fix (PR 9211) removed the AI workflows and stopped the nightly jobs consuming the Actions cache, about 30 minutes after public disclosure.

## Inferred facts

The chain that matters is the pivot sequence: issue text to prompt injection to workflow execution to poisoned cache to publish token to registry publish. Each step is documented across the five sources. The claim that the injected issue was the specific entry point is the researcher's account, corroborated by the fix removing the workflow. This is an indirect prompt-injection supply-chain attack where the LLM component is the pivot, not the payload.

## Autonomy assessment

The compromised component was itself an AI agent: a triage workflow that read untrusted GitHub issues and ran with repository credentials. The injected instructions rode content the workflow was designed to consume. Oversight was nil by design. Triage runs unattended. The remediation removed the agent from the credential path entirely, which is the instructive design outcome.

## Framework mapping

Of the five cases this one maps most cleanly onto ATLAS: AML.T0051 LLM Prompt Injection (indirect, via issue content) chained into classic ATT&CK supply-chain steps. T1552 Unsecured Credentials or T1528 Steal Application Access Token for the npm token, and T1195 Supply Chain Compromise for the poisoned release. The detection hooks that did fire in the real world were registry-side. StepSecurity and Socket both flagged the anomalous postinstall script and the break from trusted-publishing provenance, independent of anything the maintainer saw.

## Triage record

LLM rationale and heuristic scores are recorded in the evidence chain and in `results/triage_cases.json`.
