# ADR-0009: Finish AskOverlay small, and split the test-agent idea out as SapienZero

- Status: Accepted
- Date: 2026-10-16
- Related: ADR-0003 (screen context via vision) and ADR-0008 (pointing evidence) stay in force. Replaces the idea of pivoting
  this product into a test agent, which was drafted on the branch `docs/plan-v0.1` (archived under the tag
  `archive/sapienzero-plan-v0.1`).

## Context

- On 2026-10-12, after the pointing evaluation (ADR-0008), the owner judged "show me where" modest as a product and drew up a
  much larger idea: an AI test agent that runs plain-English tests in an isolated background browser. A full plan for it
  (vision, requirements, design, process) was written on a branch of this repository.
- That idea has a different user, different architecture and a much larger scope. Keeping both in one repository would blur
  both, and the documentation system built for the larger project would bury this small one.
- The owner also wants AskOverlay to survive and be finished as a small, smooth, working project, not abandoned.

## Options considered

1. **Pivot this repository into the test agent.** Loses a working, measured product and mixes two histories.
2. **Abandon AskOverlay.** Wastes the working backend, client and evaluation.
3. **Split: finish AskOverlay small here, build the test agent in a new repository** (this ADR). Both stay understandable.

## Decision

- The test-agent project is **SapienZero**, in its own repository: `github.com/brindeshwar/sapienzero`. Nothing of it is built here.
- The branch `docs/plan-v0.1` and the tag `archive/sapienzero-plan-v0.1` are kept as an **archive** and are never merged
  into this product's `main`.
- AskOverlay is **finished small**, in this order: (1) the screen-reading feature that ADR-0003 designed but never built
  ("OCR" in the owner's words; implemented with a vision model, as ADR-0003 decided, not with Tesseract); (2) a frontend
  polish pass; (3) Docker, VM and HTTPS deployment, last.
- The lightweight documentation system proven in the plan (one ADR per file, a status file, `AGENTS.md`, a docs checker in CI)
  is kept here in a reduced form. The heavy parts (requirements catalogue, roadmap with gates, architecture documents, process
  handbook) are not needed for a small project and live only in SapienZero.

## Consequences

- This repository's scope is small and bounded; new feature ideas go to SapienZero or to the "Future work" list, not here.
- Reusable work flows one way: SapienZero may reuse ideas and the evaluation method from here, with the source commit recorded.
  This repository does not depend on SapienZero.
- The archived plan is still readable, so nothing is lost; SapienZero's `docs/05-evaluation/predecessor-evidence.md` summarises
  the evidence from this product.

## How we will know it was right

AskOverlay reaches a state where a new user can run it, ask about their screen, and get a correct, grounded answer, with the
tests green and the documentation true, without further scope growth.
