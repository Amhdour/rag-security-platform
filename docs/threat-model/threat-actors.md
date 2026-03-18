# Threat actors

## A1 — External prompt attacker

- Goal: steer model/tool behavior through malicious instructions.
- Relevant surfaces: user prompts, retrieved documents, context windows.
- **Implemented detection/evidence points:** adversarial harness prompt-injection and policy-bypass scenarios.

## A2 — Poisoned content publisher

- Goal: place malicious or misleading content in retrievable sources.
- Relevant surfaces: indexed docs, authoritative-looking false guidance, hidden overrides.
- **Implemented detection/evidence points:** retrieval-poisoning fixture pack and scoring.

## A3 — Insider/operator with artifact access

- Goal: alter evidence after generation to influence governance outcomes.
- Relevant surfaces: artifact filesystem, replay/eval/Launch Gate outputs.
- **Implemented detection/evidence points:** integrity manifest verification and Launch Gate blocker behavior.

## A4 — Over-privileged tool invoker

- Goal: exfiltrate restricted data through tool calls or output transforms.
- Relevant surfaces: tool invocation context, model outputs, summarized restricted content.
- **Implemented detection/evidence points:** output leakage scenarios and tool-related warning/fail semantics in harness.

## A5 — Misconfigured deployment owner (non-malicious)

- Goal: none (accidental risk through drift/fallbacks/staleness).
- Relevant surfaces: source-mode fallback, stale evidence, schema drift.
- **Implemented detection/evidence points:** Launch Gate checks for freshness, compatibility, and blocked mismatches.
