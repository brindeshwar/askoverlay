# Interfaces

Status: Draft v0.1. The contracts that people, coding agents and CI systems rely on. Changing anything here is a public
change: it needs an ADR if breaking, a changelog entry, and a version bump per the
[engineering handbook](../06-process/engineering-handbook.md). Implements FR-40 to FR-45.

All interfaces are **thin adapters over the same core** ([HLD](hld.md)). They contain no business logic: no verdict
computation, no policy, no storage rules.

## 1. Command line (FR-40, FR-43)

The command name is provisional (`testagent` below).

| Command | Purpose |
|---|---|
| `testagent run <file-or-dir-or-> [--url URL] [--tag T] [--headed] [--approvals auto\|agent\|human] [--strict] [--budget-steps N] [--budget-seconds N] [--json]` | Run one test, a directory of tests, or standard input; prints a summary; exit code follows the verdict |
| `testagent runs list [--status S] [--limit N]` | List recent runs |
| `testagent runs show <run_id> [--json]` | Verdict, reason, cost, assertions, artifact list |
| `testagent runs events <run_id> [--after SEQ] [--follow] [--json]` | Print the event stream; `--follow` streams until the run ends |
| `testagent runs pause\|resume\|cancel <run_id>` | Run control |
| `testagent approvals list [--run RUN]`, `testagent approve <approval_id> [--note T]`, `testagent deny <approval_id> [--note T]` | Human supervision |
| `testagent report <run_id> --format html\|json\|junit [--out PATH]` | Render a report |
| `testagent serve --mcp [--transport stdio\|http] [--host H] [--port P]` | Start the MCP server (R2) |
| `testagent doctor` | Check the environment: browser installed, model key present, folders writable, clock sane |
| `testagent clean [--older-than 30d]` | Apply retention to the local run store |

**Exit codes:** 0 passed, 1 failed, 2 inconclusive, 3 blocked, 4 error, 5 usage. When running several tests the code is the
worst result, ordered error > blocked > failed > inconclusive > passed (a CI job must never turn green on an error).

**Output:** human-readable by default; `--json` prints one JSON object (or NDJSON for event streams) and nothing else on
standard output; logs go to standard error.

## 2. MCP server (FR-41, R2)

Transports: **stdio** (default, started by the client; trust is the local process) and **streamable HTTP** (bind to
localhost by default; bearer token required; validate `Origin`; refuse to listen on all interfaces unless explicitly
configured). The server is a stateless adapter: all state lives in the run store, so a restart loses nothing.

### Tools

| Tool | Arguments | Returns | Notes |
|---|---|---|---|
| `start_run` | `test` (a path under the configured test root, **or** an inline test object), `approvals` (`auto`/`agent`/`human`), `strict?`, `budgets?`, `client_request_id?` | `{run_id, status}` | Idempotent on `client_request_id`. Returns immediately; the run proceeds in the background |
| `get_run` | `run_id` | `{status, verdict?, reason?, summary, cost, assertions[], artifacts[], pending_approvals[]}` | Cheap; safe to poll |
| `get_events` | `run_id`, `after_seq?`, `limit?` | `{events[], next_seq, finished}` | The main monitoring tool; exactly-once by sequence number |
| `wait_for_run` | `run_id`, `timeout_s` (max 60), `until` (`finished`, `approval`, `any_event`) | `{reached, status, next_seq}` | A bounded long-poll so agents do not busy-loop |
| `approve_action` / `deny_action` | `run_id`, `approval_id`, `note?` | `{ok}` | Idempotent; unknown or expired ids give a clear error |
| `pause_run` / `resume_run` / `cancel_run` | `run_id` | `{status}` | Cancel completes within 5 seconds |
| `list_runs` | `status?`, `limit?` | `{runs[]}` | |
| `list_tests` | `dir?`, `tag?` | `{tests[]}` | Tests under the configured root only |
| `get_artifact` | `run_id`, `artifact_id` | resource link or inline text (screenshots as images) | Size-limited; redacted artifacts only |

### Resources (read-only, optional)

`testagent://runs/{id}/report` (HTML or JSON), `testagent://runs/{id}/events` (NDJSON), `testagent://suites/{name}`.

### Behaviours that make supervision work

- **Plain tools first.** Everything works with the tools above and polling. Progress notifications and client elicitation
  are used when the client supports them (for example, asking the user to approve in the client's own UI) but are never
  required. MCP's long-running "Tasks" feature is experimental and moving into an extension
  ([blog](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)); it will be an optional adapter, not a
  dependency (ADR-0012).
- **Tool descriptions are untrusted input to the client** and must stay factual and short. The server never embeds page
  content or secrets in descriptions or errors.
- **Errors are structured**: `{code, message, retryable, hint}`. Codes include `run_not_found`, `invalid_test`,
  `approval_expired`, `policy_denied`, `budget_exceeded`, `unavailable`.
- **Output is bounded.** Large events (snapshots) are referenced, not inlined; `get_events` pages by `limit`.

### Recommended supervision loop for a coding agent

1. `start_run(test, approvals="agent")` and keep the `run_id`.
2. Loop: `wait_for_run(run_id, until="any_event", timeout_s=30)`, then `get_events(after_seq=next_seq)`.
3. On `approval.requested`: read the action, class and reason; decide against the task's own rules; call `approve_action`
   or `deny_action`. When unsure, **deny** (a denied required step ends the run *blocked*, which is safe and visible).
4. On `warning` events (`stall_risk`, `slow_model`): optionally `pause_run`, adjust, or `cancel_run`.
5. When `finished`: `get_run` for the verdict. On `failed`, read the failing assertion and linked evidence; on
   `inconclusive`, read the missing expectations; never treat `inconclusive` or `error` as a pass.

## 3. REST API with event streaming (FR-45, R5)

Versioned under `/v1`. OpenAPI document published and contract-tested. All requests carry `Authorization: Bearer`.

| Method and path | Purpose |
|---|---|
| `POST /v1/runs` (header `Idempotency-Key`) | Create a run; returns `202` with `{run_id}` |
| `GET /v1/runs/{id}` | Run state and verdict |
| `GET /v1/runs/{id}/events?after=SEQ` | Server-sent events; each event's `id` is its `seq`, so `Last-Event-ID` resumes exactly; a heartbeat comment every 15 s keeps proxies open |
| `POST /v1/runs/{id}/pause\|resume\|cancel` | Control |
| `POST /v1/runs/{id}/approvals/{aid}` body `{decision, note}` | Resolve an approval |
| `GET /v1/runs/{id}/artifacts/{aid}` | Redirect (signed URL) to the artifact |
| `GET /healthz`, `GET /readyz`, `GET /metrics` | Liveness, readiness (database and queue reachable), Prometheus metrics |

Errors follow RFC 9457 problem details. Rate limits return `429` with `Retry-After`. Pagination uses opaque cursors.

## 4. Event stream formats

- **NDJSON** (CLI, files): one event per line, exactly the envelope in the [LLD](lld.md) section 3.
- **SSE** (REST): `id: <seq>`, `event: <type>`, `data: <payload JSON>`.
- **MCP**: events returned in `get_events` as JSON objects with the same envelope.

A consumer that stores `next_seq` can always resume without loss or duplication (FR-31).

## 5. Reports (FR-26)

- **JSON** (`report.json`, schema versioned): run, test, verdict and reason, per-expectation result with assertion kind
  (`deterministic` or `model_judged`), steps, evidence references, cost and timing.
- **HTML**: a self-contained page: verdict banner, expectation table, step timeline with screenshots, failure
  explanation (expected versus actual, last good step), links to the trace. Keyboard-operable and readable in light and
  dark themes (NFR-15). Contains no secrets.
- **JUnit XML**: one `<testcase>` per test; `failed` maps to `<failure>`, `error` and `blocked` to `<error>`,
  `inconclusive` to `<failure type="inconclusive">` (a CI job must not treat it as a pass); attachments link to artifacts.

## 6. Stability and versioning

- The test-file `version`, event `schema_version`, report schema version and API path (`/v1`) are independent.
- Additive changes (new optional fields, new event types) are non-breaking: consumers must ignore unknown fields.
- A breaking change needs an ADR, a new version, and a deprecation period of at least one minor release with a warning
  in the output (NFR-14).
