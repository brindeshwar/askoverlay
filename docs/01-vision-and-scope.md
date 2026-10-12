# Vision and scope

Status: Draft v0.1. Related decisions: [ADR-0009](decisions/README.md) (product direction, proposed).

## 1. The problem

Manual testing is slow, repetitive and expensive, and it is the part of software quality that has resisted automation:

- **Scripted tests** (Selenium, Playwright, Cypress) are fast and deterministic, but someone must write and maintain
  them, and they break whenever the interface changes (a renamed button, a moved field).
- **Manual testers** adapt to change and can follow plain instructions, but they are slow, cost money, and cannot run
  at 3 a.m. for every commit.
- **Coding agents** now write and change software quickly, but they have no safe, reliable way to *check the running
  application like a user would* and get an honest verdict they can act on.

The gap: *run a plain-English test against a real application, in the background, and return a verdict you can
trust, with evidence.*

## 2. The idea

An **AI test agent**. A test is written the way a person would describe it. The agent plans the steps, drives an
isolated headless browser, checks the expected outcomes, and reports **passed / failed / inconclusive / blocked / error**
with screenshots, a trace and a step log.

Two design commitments define the product:

1. **The verdict is computed, not opined.** The model proposes actions and assertions; the verdict follows
   deterministically from the assertions that were actually executed and recorded with evidence. The model cannot
   simply declare "passed". A test that ends without evaluating every expectation is *inconclusive*, never *passed*.
   (ADR-0011.) The worst failure of a testing tool is a false pass; this is the main defence.
2. **Supervision is a choice, and one mechanism.** Every run produces an append-only event stream. A person in a
   terminal, a coding agent over MCP, and a CI job all read the same stream and use the same controls (pause, stop,
   approve, deny). *Autonomous*, *watched by an agent* and *watched by a human* are settings of one engine.

## 3. Who it is for

| Persona | Need | How they use it |
|---|---|---|
| **P1: Developer working with a coding agent** | The agent changed the code; is the app still working? | The coding agent calls the tool over MCP, reads events, gets a verdict, and fixes what failed |
| **P2: Small team without a QA engineer** | Regression checks without writing and maintaining scripts | Plain-English tests in the repository, run in CI on every pull request |
| **P3: QA engineer** | Spend time on judgement, not repetition | Delegate routine flows; review verdicts and evidence; promote good runs to fast replay scripts |
| **P4: The owner (first user)** | A real tool to use on real projects, and a defensible portfolio project | Dogfooding on their own web projects |

## 4. Goals and success measures

| Goal | Measure (see [evaluation strategy](05-evaluation/evaluation-strategy.md)) | R1 target |
|---|---|---|
| G1. Verdicts can be trusted | False-pass rate on seeded bugs; correct-pass rate on the clean app | Missed bugs <= 20%; clean-app correct pass >= 90% |
| G2. Survives interface change | Correct verdicts after harmless UI rearrangement | >= 80% |
| G3. Repeatable | Same verdict across repeated runs | >= 90% of tests identical over 3 runs |
| G4. Safe by default | Safety canaries (off-allow-list actions, secret leaks, obeyed injected instructions) | 0 of each |
| G5. Practical | Median time per test; cost per test reported | <= 3 minutes median |
| G6. Easy to supervise | A coding agent can start, watch, pause, approve and stop a run using only the MCP tools | Demonstrated end to end (R2) |
| G7. Recoverable project | A fresh agent can resume from the repository alone | Cold-start drill passes (every release) |

## 5. Scope

**In scope for the first release (R1):** web applications; tests written in plain English with explicit expected
outcomes; headless background execution in an isolated browser; verdict and evidence; event stream; command line;
safety rails (site allow-list, secret handling, approvals, budgets); local-first, with the user's own model key.

**Planned later (see the [roadmap](03-features-and-roadmap.md)):** MCP server and supervision modes (R2); resilience
(self-healing, record-and-replay, the vision "pointing" fallback) (R3); exploratory testing (R4); service mode with a
scalable API and worker pool (R5); desktop and mobile applications, test generation from specifications (R6).

**Explicitly out of scope (non-goals):**

- A general "do anything on my computer" agent (sending email, shopping, personal chores). Different risk profile and
  best done through APIs. Revisit only as a separate project.
- Replacing human judgement about design, usability and intent, or testing on physical devices.
- Operating on the user's own desktop in the foreground. The agent works in an isolated browser, not your screen.
- Any feature that needs the model to see credentials in clear text.

"Full manual testing" is the long-term **direction**, not a promise. The honest claim is *"automates the routine,
repeatable part of manual testing and says clearly when it cannot decide."*

## 6. Where this fits (honest positioning)

This area is crowded and moving fast. Playwright itself now ships AI "planner, generator and healer" agents built on
MCP, and commercial products offer natural-language testing on the same stack
([overview](https://testdino.com/blog/playwright-ai-ecosystem); mostly vendor material, to be re-checked against the
official Playwright documentation before any competitive claim). General computer-use agents are advancing quickly
but remain unreliable on long tasks (OSWorld 2.0 reports roughly 13-20% full-task completion; sources disagree
and are mostly self-reported; see [OSWorld 2.0](https://snorkel.ai/leaderboard/os-world-2-0/)).

We do **not** claim to be better than these. The defensible position is narrower:

- **Measured**: every claim comes from a pre-registered experiment with stated limits.
- **Supervisable by design**: one event stream, three supervision modes, MCP-native.
- **Local-first and private**: runs on your machine with your own key; nothing is sent to a service we operate.
- **Honest verdicts**: computed from assertions, with "inconclusive" as a first-class outcome.

## 7. Principles

1. **Measure before building.** A pass bar is written before any result exists.
2. **Computed verdicts.** Never trust the model's own conclusion.
3. **Safe by default.** Allow-lists, approvals for risky actions, secrets never shown to the model, budgets on everything.
4. **Local-first, service-ready.** One core engine; a scalable service mode is designed now and built only when needed.
5. **The repository is the memory.** If it is not written down in the repository, it does not exist.
6. **Simplest thing that works.** Add a framework, model or service only with a written reason.

## 8. Constraints and assumptions

- One owner, part-time (competing with exam preparation). Scope is staged with kill criteria so partial progress
  is still valuable.
- Free-tier model quotas and latency (observed: 2 to 17 seconds to the first token; some models rate-limited).
  Design must tolerate slow and failing model calls.
- Windows is the owner's development machine; CI runs on Linux and Windows.
- Assumption to verify early: page-structure snapshots (the accessibility tree) give the model enough information to
  act reliably on typical web applications, with vision as a fallback.

## 9. Relationship to the earlier "AskOverlay" overlay product

The first product (a desktop overlay that answers questions about your screen, with a pointing capability) taught three
things that carry over: the **evaluation method** (pre-registered, blind, with honest confidence ranges), the
**LLM plumbing** (provider-neutral error handling, fallback model, stateless server), and a **vision pointing model**
that becomes the test agent's fallback tool. The overlay UI and demo-quota machinery do not carry over. What happens to
that code is decided in ADR-0009 and tracked in [STATUS](status/STATUS.md).
