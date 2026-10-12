# ADR-0012: The MCP surface is plain tools; the experimental Tasks feature is optional

- Status: Proposed
- Date: 2026-10-12
- Related: Specified in [interfaces](../04-architecture/interfaces.md) section 2. Implements FR-41 and FR-34.

## Context

A coding agent must be able to start a run, watch it, answer approval requests, pause and cancel it, and read the result.
Runs take minutes. MCP's built-in long-running mechanism, **Tasks**, is **experimental** in the 2025-11-25 specification and the
2026-07-28 release candidate moves it into an extension, so its shape is still changing. MCP also offers progress
notifications and client elicitation (asking the user for input), which clients may or may not support. Streamable HTTP is the
current network transport.

## Options considered

1. **Tasks-first.** Idiomatic for long jobs, but depends on an unstable feature and on client support.
2. **Plain tools with polling**: `start_run` returns immediately; `get_events(after_seq)` and a bounded `wait_for_run` provide
   monitoring; approvals are tools. Works with any MCP client today.
3. **Resource subscriptions** for event streams. Elegant; client support is uneven and unverified.

## Decision

We will build **option 2** as the contract, and treat the others as optional enhancements behind the same adapter:
progress notifications and elicitation when the client supports them; a Tasks adapter once the specification stabilises.
Everything stateful lives in the core and its run store, so the MCP adapter is stateless and a restart loses nothing. Supported
transports: stdio (default) and streamable HTTP (localhost, bearer token, origin validation). The official `mcp` Python SDK is the
default implementation; a spike compares it with the standalone `fastmcp` before commitment (tracked as open low-level question 3 in the LLD).

## Consequences

- Works with every MCP client, now; agents poll with bounded waits rather than receiving pushes.
- Slightly chattier than a push design; acceptable at this scale.
- The contract is ours and versioned, not tied to a moving part of the specification.
- Adding Tasks later is an adapter, not a redesign.

## How we will know it was right

A real MCP client completes the R2 exit scenario using only these tools: start, watch, approve, pause, cancel, read the report. The
spike confirms the chosen SDK handles both transports and bounded waits.
