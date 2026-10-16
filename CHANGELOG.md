# Changelog

All notable user-visible changes are recorded here, newest first, in the
[Keep a Changelog](https://keepachangelog.com/) format.

## [Unreleased]

### Added
- Documentation system: one decision record per file under `docs/decisions/` (ADR-0001 to ADR-0009), a status file,
  `AGENTS.md`/`CLAUDE.md`, and a docs checker (`tools/check_docs.py`) that runs in CI.
- LangGraph agent with `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` as fallback; bring-your-own-key plus a lifetime
  demo of 10 requests per device; the client holds the conversation history.
- Pointing evaluation harness under `evals/pointing/` and its recorded result (ADR-0008).

### Changed
- The single decision-log file `docs/ADR.md` was split into one file per decision.
- Docker: healthcheck and tighter ignore rules (not yet built or tested; deployment work comes last).

### Removed
- Payments and Google sign-in (see ADR-0005).

The test-agent idea that grew out of this project moved to its own repository, SapienZero (ADR-0009).
