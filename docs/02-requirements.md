# Requirements

Status: Draft v0.1. Source of truth for *what* the system must do. How is in [HLD](04-architecture/hld.md) and
[LLD](04-architecture/lld.md); when is in the [roadmap](03-features-and-roadmap.md).

**Conventions.** "Shall" is mandatory. Priority uses MoSCoW: **M**ust, **S**hould, **C**ould. "Rel" is the first
release that must satisfy it (R1 to R6). Every requirement has an acceptance criterion (AC) that a test or an
experiment can check; a requirement without one is not a requirement. IDs are permanent: never reuse one.

## Functional requirements

### Authoring: describing a test

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-01 | A test is a file with plain-English `steps` and explicit `expect` outcomes (YAML; Markdown later) | M | R1 | A valid file parses; an invalid one fails with a message naming the field and line |
| FR-02 | A test declares `id`, `title`, `base_url`, `steps`, `expect`, and optionally `secrets`, `tags`, `allow_origins`, `mutation_policy`, `budgets`, `strict` | M | R1 | Schema published and validated; unknown fields are rejected |
| FR-03 | A test can be given inline on the command line or standard input | S | R1 | `run -` reads a test from stdin |
| FR-04 | A directory of tests can be run, filtered by tag or id | S | R1 | `run tests/ --tag smoke` runs only matching tests |
| FR-05 | A test can be parameterised with data rows | C | R3 | One run record per row |

### Execution: running it in the background

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-10 | Each run uses a fresh, isolated browser context (no shared cookies, storage or profile) | M | R1 | Two runs cannot see each other's state (tested) |
| FR-11 | Runs are headless by default and never touch the user's screen, mouse or keyboard; headed mode exists for debugging | M | R1 | Running a test does not change the foreground window (checked manually and by design) |
| FR-12 | The agent observes pages through an accessibility-tree snapshot with stable element references | M | R1 | Every action targets a reference from the latest snapshot |
| FR-13 | Actions available: navigate, click, type, select, press key, hover, wait for condition, go back, screenshot, read text | M | R1 | Each has a contract test against the test app |
| FR-14 | After each action the agent verifies the outcome (page changed, no new errors) and records it | M | R1 | Each step event has a `verification` field |
| FR-15 | Budgets cap steps, wall time and model tokens; exceeding one ends the run as *inconclusive* | M | R1 | A test with a tiny budget ends inconclusive with reason `budget` |
| FR-16 | Loops and stalls (repeating the same action without progress) are detected and end the run | M | R1 | A seeded dead-end page ends inconclusive with reason `stalled` |
| FR-17 | Every external call (browser action, model call) has a timeout | M | R1 | No unbounded wait exists (reviewed; fault-injection test) |
| FR-18 | Pop-ups, new tabs, frames and JavaScript dialogs are handled | S | R1 | Test-app pages cover each |
| FR-19 | File upload and download are available under policy | C | R3 | Policy-gated tests |

### Verdict and evidence: the trust core

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-20 | The verdict is one of `passed`, `failed`, `inconclusive`, `blocked`, `error`, `cancelled` | M | R1 | Enumeration in the schema; each reachable in tests |
| FR-21 | The verdict is **computed from recorded assertions**, never from the model's own statement of success (ADR-0011) | M | R1 | A test where the model "declares success" without assertions ends inconclusive |
| FR-22 | Every `expect` item needs at least one recorded assertion; otherwise the run is inconclusive | M | R1 | Property test over generated runs |
| FR-23 | Assertions are *deterministic* (text, URL, element state, count, attribute) or *model-judged*; model-judged ones are flagged in every report; `strict` mode forbids them | M | R1 | Report shows the kind; strict run rejects model-judged |
| FR-24 | Evidence is kept per run: step log, snapshots, screenshots, console and network errors, browser trace | M | R1 | Artifacts listed in the run record and readable |
| FR-25 | A failure report names the failing assertion, expected versus actual, the last good step, and evidence | M | R1 | Report contains those fields for every seeded bug |
| FR-26 | Reports are available as JSON and HTML (R1) and JUnit XML for CI (R1/R2) | M | R1 | Files validate against their schemas |
| FR-27 | Known secrets and common personal-data patterns are redacted from artifacts and events | S | R1 | Canary secret never appears in any artifact |
| FR-28 | A re-run policy exists for suspected flakiness, and flaky results are labelled as such | S | R3 | Flake label appears when verdicts differ across repeats |

### Supervision: one mechanism, three modes

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-30 | Every run emits an append-only, ordered event stream with a per-run sequence number | M | R1 | Replaying events reconstructs the run summary exactly |
| FR-31 | A consumer can resume reading from a given sequence number without loss or duplication | M | R1 | Property test: any prefix plus the rest equals the whole |
| FR-32 | A run can be paused, resumed and cancelled | M | R1 | State-machine tests |
| FR-33 | Risky actions raise an approval request; no answer within the timeout means *deny* | M | R1 | Timeout test ends run `blocked` |
| FR-34 | Approvals are routed by mode: `auto` (policy decides), `agent` (the calling agent), `human` (terminal prompt or web view) | M | R2 | End-to-end tests for each mode |
| FR-35 | The command line can follow a run live | S | R1 | `runs events --follow` streams until finished |

### Interfaces

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-40 | A command-line interface covers run, list, show, events, cancel, approve, deny, report, doctor | M | R1 | Documented in [interfaces](04-architecture/interfaces.md); each command tested |
| FR-41 | An MCP server (stdio and streamable HTTP) exposes the run, watch, approve, cancel and report tools | M | R2 | Passes a conformance check with a real MCP client |
| FR-42 | A Python API exposes the same operations | S | R2 | Documented example runs in CI |
| FR-43 | Exit codes map to verdicts (0 passed, 1 failed, 2 inconclusive, 3 blocked, 4 error, 5 usage) | M | R1 | Table-driven test |
| FR-44 | A ready-to-use CI recipe (GitHub Actions) runs tests and publishes reports | S | R2 | Recipe runs in this repository's CI against the test app |
| FR-45 | A REST API with server-sent events exposes the same operations (service mode) | S | R5 | OpenAPI document and contract tests |

### Safety

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-50 | Navigation is limited to an **origin allow-list**; anything else is denied and recorded | M | R1 | Canary: a link to a disallowed origin is never opened |
| FR-51 | Private network ranges and cloud metadata endpoints are blocked unless explicitly allow-listed | M | R1 | SSRF tests (10.x, 169.254.169.254, localhost redirects) |
| FR-52 | Secrets are referenced by name, resolved only at execution time, and never appear in prompts, events, logs or artifacts | M | R1 | Canary secret search over all outputs finds nothing |
| FR-53 | Each action has a class (read, interact, submit, destructive); `mutation_policy` sets allow, ask or deny per class | M | R1 | Table-driven policy tests |
| FR-54 | Page content is treated as untrusted data: instructions found in a page are never followed | M | R1 | Planted-instruction tests: 0 of 5 obeyed |
| FR-55 | The model has no tool that runs arbitrary code, reads local files, or changes browser security settings | M | R1 | Tool registry review plus a test that lists tools |
| FR-56 | A global kill switch and concurrency limits exist | M | R1 | Kill stops all runs within 5 seconds |

### Operations (local mode)

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-60 | `doctor` checks browser install, model key, write access, and time budget sanity | S | R1 | Clear pass/fail per check |
| FR-61 | A local run store keeps runs and artifacts with a retention setting and a cleanup command | S | R1 | Old runs removed after retention |
| FR-62 | Logs are structured and carry the run id | M | R1 | Log lines parse as JSON |
| FR-63 | Configuration comes from environment and file, validated at start | M | R1 | Invalid config fails fast with a clear message |
| FR-64 | Model access is provider-neutral, bring-your-own-key, with an optional fallback model and classified errors | M | R1 | Carried over from the earlier backend; fake-model tests |

### Resilience (R3)

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-70 | Locating elements adapts to interface change (role and name first, then context, then vision) | S | R3 | UI-change robustness >= 85% |
| FR-71 | A successful run can be compiled to a deterministic Playwright script and replayed cheaply | S | R3 | Replay verdict equals agent verdict on the suite |
| FR-72 | When a snapshot is not enough, a vision pointing tool is used as a fallback | S | R3 | Fallback invoked and correct on seeded canvas-like pages |
| FR-73 | When a replayed script breaks, the agent takes over and reports the drift | S | R3 | Drift reported on UI-change variants |

### Exploratory testing (R4) and service mode (R5)

| ID | Requirement | P | Rel | AC |
|---|---|---|---|---|
| FR-80 | An explore mode pursues a goal under a budget and reports anomalies | C | R4 | Finds >= 60% of seeded exploratory bugs |
| FR-81 | Detectors: console errors, failed requests, broken links, accessibility violations, visual change | C | R4 | Each detector has a seeded case |
| FR-82 | Findings become reproducible bug reports with steps and evidence | C | R4 | A report can be re-run as a test |
| FR-90 | Runs go through a durable queue to a pool of workers | S | R5 | Worker crash re-queues the run (chaos test) |
| FR-91 | Tenants are isolated and have quotas and fair scheduling | S | R5 | Noisy-neighbour test |
| FR-92 | Schedules and webhooks trigger and report runs | C | R5 | Scheduled run fires; webhook delivered with retry |
| FR-93 | Artifacts are stored durably with lifecycle rules | S | R5 | Objects expire per policy |
| FR-94 | Metrics, traces and dashboards exist for runs and the platform | S | R5 | Dashboard shows queue depth, verdicts, latency |
| FR-95 | The API is authenticated and authorised per tenant | M | R5 | Access-control tests |

## Non-functional requirements

| ID | Quality | Requirement | How measured |
|---|---|---|---|
| NFR-01 | Correctness | On the seeded-bug suite: bugs caught >= 80% and **false-pass rate <= 15%** at R1 (false pass <= 10% by R3); clean-app correct-pass rate >= 90% | Evaluation strategy, pre-registered |
| NFR-02 | Repeatability | Same verdict on >= 90% of tests over 3 repeats | Evaluation suite |
| NFR-03 | Speed | Median test <= 3 minutes, p95 <= 8 minutes (reference model and network) | Evaluation suite timings |
| NFR-04 | Cost | Cost per run is reported; a default budget ceiling applies and is configurable | Cost meter in run record |
| NFR-05 | Security | 0 safety-canary failures; no known high or critical dependency vulnerabilities at release | Canary suite; dependency scanning |
| NFR-06 | Privacy | No telemetry by default; in local mode data stays on the machine; default artifact retention 30 days | Code review; network-egress test |
| NFR-07 | Portability | Windows, macOS and Linux; Python 3.12 or newer; Chromium first | CI matrix |
| NFR-08 | Observability | Any run can be reconstructed from its events; logs structured; service mode adds traces and metrics | Replay test |
| NFR-09 | Maintainability | Core package type-checked in strict mode; lint clean; line coverage >= 80% for core (ratchet upward); every significant decision has an ADR | CI gates |
| NFR-10 | Availability (service) | API 99.5% monthly; run start latency p95 <= 15 s; event lag p95 <= 2 s | SLO monitoring |
| NFR-11 | Scalability (service) | Capacity grows roughly linearly with workers; reference design target 1,000 runs per hour, bounded by model quota | Load test; see [scaling](04-architecture/scaling-and-operations.md) |
| NFR-12 | Recoverability | Service: RPO <= 5 min, RTO <= 1 h. Project: cold-start drill passes every release | Restore drill; documentation policy |
| NFR-13 | Documentation | Every public interface documented; docs check passes in CI | `tools/check_docs.py` |
| NFR-14 | Compatibility | Event schema and test-file format are versioned; deprecations last at least one minor release | Schema tests; changelog |
| NFR-15 | Accessibility | HTML reports are keyboard-operable with sufficient contrast | Manual audit plus automated check |

## Traceability

Each requirement is verified by one of: **unit** test, **contract** test (against the seeded-bug test app),
**property** test, **fault-injection** test, **evaluation** (a pre-registered experiment), **review**, or **manual** check
(only where automation is not sensible, and stated). The test names carry the requirement id (for example
`test_fr_21_...`) so a search shows coverage; the roadmap's exit gate lists the requirements a release must satisfy.
