https://www.amhdour.cv/

# RAG Security Platform (Evaluation Layer)

This repository provides an **evaluation and evidence-generation layer** for AI Trust & Security Readiness in RAG systems and autonomous agents.

## What this project demonstrates

- Structured adversarial testing for AI systems
- Security control validation across attack scenarios
- Evidence generation for review and audit
- Launch-readiness decision support (go / no-go)

## What is implemented

- Adversarial scenario definitions (prompt injection, retrieval attacks, tool abuse)
- Evaluation pipelines for control validation
- Normalized evidence artifacts (logs, reports, replay files)
- Launch gate reporting structure

## Validation coverage

Security controls are evaluated against:
- Prompt injection attacks
- Retrieval poisoning scenarios
- Data boundary violations
- Tool misuse and escalation paths

## Evidence outputs

- Audit logs
- Evaluation reports
- Replay artifacts
- Launch gate summaries

## Reviewer quick path

1. Evaluation scenarios → `/scenarios` or `/docs`  
2. Run evaluation → `/scripts` or CLI  
3. Inspect outputs → `/outputs`  
4. Launch gate report → `/reports`  

## Role in system

- `myStarterKit` → Implementation
- `rag-security-platform` → **Evaluation & validation**
- `myStarterKit-maindashb` → Observability
- `amhdour.cv` → Evidence presentation
