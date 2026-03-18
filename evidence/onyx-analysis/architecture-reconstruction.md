# Architecture Reconstruction

**Status:** Unconfirmed  
**Basis:** derived from analysis of baseline runtime.  
**Note:** Unconfirmed: canonical runtime hook not validated in this workspace.

## Inferred Runtime Flow

1. **User → API**  
   Derived from analysis of baseline runtime: a user or API client submits a chat request to the chat backend endpoint.
2. **API → Agent Runtime**  
   Derived from analysis of baseline runtime: the request is normalized, authenticated, rate-limited, and handed into the chat execution path.
3. **Agent Runtime → Retrieval**  
   Derived from analysis of baseline runtime: the runtime can invoke search/retrieval flows to build context for the answer.
4. **Retrieval → Model Context**  
   Derived from analysis of baseline runtime: retrieved chunks/sections are filtered, merged, and prepared as model-readable context.
5. **Agent Runtime → Model**  
   Derived from analysis of baseline runtime: the LLM receives the user message plus available retrieved context and runtime instructions.
6. **Agent Runtime → Tools**  
   Derived from analysis of baseline runtime: the runtime can construct and expose enabled tools such as search, web, URL, file, Python, custom, and MCP-backed tools.
7. **Runtime → Response**  
   Derived from analysis of baseline runtime: the final answer is returned as either a streamed response or a complete non-streaming response.
