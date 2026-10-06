# Architecture

Private Assistent starts with five boundaries:

1. API: local HTTP interface.
2. Runtime: request/session orchestration.
3. Agent: AgentScope-backed assistant behavior.
4. Tools: local capabilities with security checks.
5. Memory: local session and long-term memory.

This is intentionally smaller than QwenPaw while keeping compatible ideas:
workspace-first storage, explicit tool boundaries, and local-first defaults.
