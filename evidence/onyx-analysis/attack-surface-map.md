# Attack Surface Map

**Status:** Unconfirmed  
**Basis:** derived from analysis of baseline runtime.  
**Note:** Unconfirmed: canonical runtime hook not validated in this workspace.

## Key Surfaces

- **Prompt injection**  
  Derived from analysis of baseline runtime: malicious instructions may enter through user prompts, retrieved content, or connector-fed context.
- **Connector over-permission**  
  Derived from analysis of baseline runtime: retrieval and federated connectors may expose broader data than intended if source scoping or ACL assumptions fail.
- **Tool misuse**  
  Derived from analysis of baseline runtime: enabled tools may be invoked in ways that exceed least-privilege expectations or intended task scope.
- **Identity spoofing**  
  Derived from analysis of baseline runtime: trust in request identity, propagated headers, OAuth context, or external tool identity can become a control point.
