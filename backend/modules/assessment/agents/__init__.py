"""Assessment agents — specialist tools for security assessment pipeline stages.

Each agent has:
- Clear input / output contract
- Explicit boundary (what it can and cannot do)
- Traceable output (structured JSON)
- Fallback strategy (graceful degradation when LLM is disabled)
"""
