# Retrofit Design

**Status:** Planned  
**Basis:** derived from analysis of baseline runtime.

## Proposed Additions

- **Policy layer**  
  Derived from analysis of baseline runtime: add a central decision point before model/tool execution for prompt, context, and action policy evaluation.
- **Retrieval filtering**  
  Derived from analysis of baseline runtime: enforce explicit source, ACL, and connector-scoping checks before retrieved content reaches the model.
- **Tool authorization**  
  Derived from analysis of baseline runtime: require allowlisted tool execution with user/session-aware authorization and per-tool scope checks.
- **Telemetry hooks**  
  Derived from analysis of baseline runtime: emit structured events for retrieval decisions, tool calls, identity context, and policy denials.
