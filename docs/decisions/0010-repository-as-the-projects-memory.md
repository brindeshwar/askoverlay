# ADR-0010: The repository is the project's memory

- Status: Proposed
- Date: 2026-10-12
- Related: Implemented by `AGENTS.md` and the [documentation and memory policy](../06-process/documentation-and-memory-policy.md).

## Context

Work is done in conversations with AI coding agents, across many sessions and sometimes machines. Chat history and an
assistant's local memory can disappear, differ between machines, or contain facts that are not written anywhere else. The owner
requires that after losing everything except the GitHub repository, a new agent can read it and be fully in sync. Earlier work
already showed the cost of knowledge living only in chat: dates assumed instead of read, decisions in one growing file, lessons
re-learned.

## Options considered

1. **Rely on chat history and assistant memory.** Zero effort; fragile and unreviewable.
2. **A wiki or external notes tool.** Easy to edit; separate from code, drifts, not versioned with it, not read by agents by default.
3. **Documentation in the repository, enforced by process and automation** (docs as code).

## Decision

We will treat the repository as the **only** memory. Concretely:

- `AGENTS.md` (read first by any agent; `CLAUDE.md` imports it) defines the cold-start reading order, the working agreement,
  the documentation duties and the end-of-session protocol.
- One **single source of truth** per kind of information (policy section 2); everything else links.
- **ADRs** for decisions (one file each, immutable once accepted, superseded rather than edited); **pre-registered** experiments;
  a living `STATUS.md` rewritten every session; a lessons log.
- **Docs change with code** in the same pull request, checked by a PR checklist and by `tools/check_docs.py` in CI (ADR index,
  no orphan documents, no broken links, fresh status).
- A **cold-start drill** (a fresh agent with only the repository must answer six questions and make a correct small doc change)
  before every release.
- Assistant-local memory holds pointers only.

## Consequences

- More writing per change; accepted deliberately, and kept proportionate by tables, templates and the single-source rule.
- New contributors, human or agent, onboard in about ten minutes.
- Documentation quality becomes testable (drills) rather than hoped for.
- Private data and secrets cannot be recovered from the repository by design; the policy lists them and how to recreate them.

## How we will know it was right

The cold-start drill passes (all six answers correct, small task done correctly) at R0 exit and before each release; the docs check
stays green; the number of "I did not know X" findings per drill trends to zero.
