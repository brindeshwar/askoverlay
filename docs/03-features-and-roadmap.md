# Features and roadmap

Status: Draft v0.1. Scope is defined by [requirements](02-requirements.md); this file orders it in time and sets the
**gates** that decide whether to continue.

Effort figures are rough, in *focused working days*, accurate to about plus or minus 50%, and are re-estimated at the start
of each release. Calendar time depends on the owner's weekly availability (an open question, see
[open questions](07-open-questions.md)). Nothing here is a promise of a date.

## Feature catalogue

| ID | Feature | What the user gets | Requirements | Release |
|---|---|---|---|---|
| F-01 | Plain-English test files | Write what a person would do and what should result | FR-01 to FR-05 | R1 (data-driven R3) |
| F-02 | Isolated background browser | Tests run headless, never disturbing the user | FR-10, FR-11, FR-18 | R1 |
| F-03 | Page-structure agent loop | Reliable actions through accessibility snapshots | FR-12 to FR-17 | R1 |
| F-04 | Computed verdicts and evidence | Trustworthy pass or fail, screenshots, trace, step log | FR-20 to FR-27 | R1 |
| F-05 | Event stream and run control | Live progress, pause, resume, cancel | FR-30 to FR-33, FR-35 | R1 |
| F-06 | Command-line tool | `run`, `runs`, `report`, `doctor` | FR-40, FR-43, FR-60 to FR-63 | R1 |
| F-07 | Safety rails | Allow-list, SSRF block, secret handling, approvals, budgets | FR-50 to FR-56 | R1 |
| F-08 | Provider-neutral model access | Bring your own key, fallback model, classified errors | FR-64 | R1 |
| F-09 | MCP server | A coding agent starts, watches, approves, stops runs | FR-41 | R2 |
| F-10 | Supervision modes | Autonomous, agent-supervised or human-supervised | FR-34 | R2 |
| F-11 | Python API and CI recipe | Use it in code and in GitHub Actions; JUnit reports | FR-42, FR-44, FR-26 | R2 |
| F-12 | Record and replay | Turn a good run into a fast, cheap script | FR-71, FR-73 | R3 |
| F-13 | Self-healing and vision fallback | Survive UI change; handle canvas-like pages | FR-70, FR-72 | R3 |
| F-14 | Flake handling | Re-run policy and honest "flaky" labels | FR-28 | R3 |
| F-15 | Exploratory mode | The agent hunts for bugs toward a goal | FR-80 to FR-82 | R4 |
| F-16 | Service mode | Scalable API, queue, worker pool, multi-tenant, dashboards | FR-45, FR-90 to FR-95 | R5 |
| F-17 | Beyond the web | Desktop apps, mobile, tests generated from specifications | to be specified | R6 |

## Releases

### R0: Plan and review (now)

- **Scope:** this documentation set; decisions ADR-0009 to ADR-0013; documentation checker; GitHub templates; repository
  hygiene; CI tiers 0 and 1 ([CI/CD](06-process/ci-cd.md)).
- **Exit gate:** an outside reviewer has read the brief and design and their feedback is applied; ADR-0009 is accepted
  or rejected; the plan is merged to the main line and tagged `plan-v0.1`; the cold-start drill passes on the merged docs.
- **Effort:** 3 to 5 days.

### R1: Core agent, local, command line

Built in five steps, each ending in something that runs. **Step 1 freezes the pass bar before any agent exists.**

| Step | Content | Evidence it is done |
|---|---|---|
| R1.0 Test bed | A small web store (login, list, cart, checkout form) with switchable seeded bugs and layout variants; the 30-test suite; the **frozen pass bar** committed | Bar and suite committed; test app has its own tests |
| R1.1 Spike | Minimal loop (browser, snapshot, graph, assertions) | First measurement against the bar, honestly reported; **gate** |
| R1.2 Engine | Event store, run state machine, verdict computation, CLI | FR-20 to FR-35, FR-40 pass |
| R1.3 Safety | Allow-list, SSRF block, secrets, approvals, injection canaries | FR-50 to FR-56 pass; canary suite green |
| R1.4 Reports | JSON, HTML, JUnit; cost and time reporting | FR-24 to FR-26 pass |

- **Exit gate (all must hold, measured on the frozen suite; see [evaluation](05-evaluation/evaluation-strategy.md)):**
  clean-app correct pass >= 90%; seeded bugs caught >= 80%; UI-change robustness >= 80%; repeatability >= 90%;
  0 safety-canary failures; median test <= 3 minutes.
- **Effort:** 15 to 25 days.
- **Kill or rescope criteria:** if the R1.1 spike misses a bar by more than 10 points, one structured mitigation attempt
  is allowed (documented in an ADR). If it still misses, stop and decide again (ADR) rather than continue building.
  If R1 has used 40 focused days without passing its gate, hold a decision review.

### R2: Supervisable by other agents

- **Scope:** MCP server (stdio and streamable HTTP); the three approval modes; Python API; GitHub Actions recipe; JUnit.
- **Exit gate:** a real MCP client (a coding agent) starts a run, watches events, pauses, approves a risky step, cancels
  another run, and reads a report using only the MCP tools; the CI recipe runs in this repository; the run is recorded
  as an example in the documentation.
- **Effort:** 8 to 12 days.

### R3: Resilient and cheap to repeat

- **Scope:** compile runs to Playwright scripts and replay; take over when a replay drifts; self-healing locators; the
  vision pointing fallback (reusing the earlier pointing work); data-driven tests; flake labels.
- **Exit gate:** UI-change robustness >= 85%; replay verdicts equal agent verdicts on the suite; replay costs at least
  10 times fewer model tokens than agent mode on the suite; false-pass rate <= 10%.
- **Effort:** 10 to 15 days.

### R4: Exploratory testing

- **Scope:** goal-driven exploration under a budget; detectors for console errors, failed requests, broken links,
  accessibility violations, visual change; findings turned into reproducible tests.
- **Exit gate:** finds >= 60% of seeded exploratory bugs with precision >= 70% (few false alarms).
- **Effort:** 10 to 15 days.

### R5: Service mode

- **Scope:** REST API with event streaming; durable queue; worker pool; object storage; multi-tenant quotas and fair
  scheduling; scheduling and webhooks; metrics, traces, dashboards; deployment recipes. Designed in
  [scaling and operations](04-architecture/scaling-and-operations.md); **built only if there is demand for it**, because
  local mode already serves P1 to P4.
- **Exit gate:** load test reaches the reference capacity on the documented hardware; chaos tests (worker kill, database
  restart) lose no runs; SLOs met for a week in staging; runbooks exist and have been followed once.
- **Effort:** 25 to 40 days.

### R6: Beyond the web

- **Scope (to be specified):** Windows desktop applications through the UI Automation tree, mobile through Appium,
  tests generated from specifications and tickets.
- **Gate:** a new ADR with its own measured feasibility before any build.

## What we are deliberately not doing

- A general computer-use or "personal chores" agent; the earlier desktop overlay; accounts and payments; any foreground
  control of the user's screen.
- Building service mode before local mode has users.
- A custom model, a custom browser driver, or a custom agent framework.

## Decision gates (summary)

| After | Decision | Inputs |
|---|---|---|
| R0 | Accept ADR-0009 (the test-agent direction) | Reviewer feedback, owner's time budget |
| R1.1 | Continue, mitigate once, or stop | Spike measurement against the frozen bar |
| R1 | Release R1; start R2 | Exit gate evidence, cold-start drill |
| R3 | Is R4 or R5 the next investment | Who is using it, what they ask for |

## Parking lot (ideas not yet scheduled)

Cross-browser (Firefox, WebKit); visual regression baselines; test impact analysis (run only affected tests);
generating tests from pull-request diffs; accessibility reporting; localisation checks; a small web UI for runs.
Ideas enter the roadmap only through a written requirement and a gate.
