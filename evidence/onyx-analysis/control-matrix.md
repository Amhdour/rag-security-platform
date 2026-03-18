# Control Matrix

**Status:** Unconfirmed  
**Basis:** derived from analysis of baseline runtime.  
**Note:** Unconfirmed: canonical runtime hook not validated in this workspace.

| Threat | Surface | Gap | Proposed control |
|---|---|---|---|
| Prompt injection | User prompts and retrieved context | Retrieved and user-supplied instructions may reach model context together | Add prompt/content separation, source-aware instruction stripping, and response-time policy checks |
| Connector over-permission | Retrieval and connector-backed data access | Access depends on correct filtering and connector scoping | Enforce fail-closed source filters, connector allowlists, and explicit ACL verification |
| Tool misuse | Runtime to built-in/custom/MCP tools | Tool availability may exceed task-specific need | Add per-tool authorization, least-privilege defaults, and policy-based tool gating |
| Identity spoofing | API auth and downstream tool identity | Identity context may be reused across boundaries without strong binding | Bind tool execution to verified user/session context and log identity propagation decisions |
