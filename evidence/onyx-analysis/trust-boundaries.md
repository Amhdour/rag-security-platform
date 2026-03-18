# Trust Boundaries

**Status:** Unconfirmed  
**Basis:** derived from analysis of baseline runtime.  
**Note:** Unconfirmed: canonical runtime hook not validated in this workspace.

## Boundary List

- **User / API**  
  Derived from analysis of baseline runtime: untrusted user input crosses into authenticated and rate-limited API handling.
- **API / Runtime**  
  Derived from analysis of baseline runtime: validated requests cross from HTTP handling into internal chat execution and state management.
- **Runtime / Retrieval**  
  Derived from analysis of baseline runtime: runtime logic delegates to search pipelines and federated retrieval functions for context assembly.
- **Retrieval / Data**  
  Derived from analysis of baseline runtime: retrieval components access indexed documents, connector-backed sources, and ACL-filtered data.
- **Runtime / Tools**  
  Derived from analysis of baseline runtime: agent execution can invoke configured built-in, custom, or MCP tools with their own downstream effects.
