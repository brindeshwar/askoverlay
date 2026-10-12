# ADR-0009: Make the product an AI test agent

- Status: Proposed
- Date: 2026-10-12
- Related: Builds on the evidence of ADR-0008 (pointing evaluation). If accepted, the product direction in ADR-0008 ("show me
  where") is superseded as the *product*, while its evidence and method stay valid. Depends on ADR-0010 to ADR-0013.

## Context

- The earlier "AskOverlay" product (a desktop overlay that answers questions about your screen and can point at controls) was
  built, measured and found modest as a product: it points at the right control about 85% of the time (about 80% for small
  controls, ADR-0008), answers take 2 to 17 seconds on a free tier, and the owner judged it not worth further investment.
- The owner's actual wish is different and larger: software that does the repetitive human work of using other software,
  in the background, without disturbing anyone. Examples named: sending an email through a web interface, preparing
  and labelling screenshots, and **replacing manual testing**.
- General computer-use agents are a crowded, fast-moving field with unreliable long-task performance (about 13 to 20% full
  completion on long professional workflows in OSWorld 2.0; sources disagree and are mostly self-reported). Playwright
  already ships AI planner, generator and healer agents on MCP, and commercial natural-language testing products exist.
  Compounding error matters: at about 80% per step, a 10-step task succeeds roughly 11% of the time if steps fail independently.
- Constraints: one owner, part-time, preparing for an exam; free-tier model quotas; a strong preference for professional,
  measured, well-documented engineering and for being able to explain every decision.

## Options considered

1. **Finish "show me where"** as originally scoped. Smallest and already measured, but the owner does not find it worth the time
   and the demo value is limited.
2. **A general "chores" agent** (email, shopping, files). Highest appeal, worst risk and measurability: personal credentials,
   irreversible actions, verification codes, no clean pass or fail, and the right mechanism for most chores is an API, not
   clicking. Crowded by well-funded products.
3. **An AI test agent** (this ADR): natural-language tests run in an isolated, headless background browser with computed,
   evidence-backed verdicts, usable standalone or supervised by a coding agent over MCP. Clear pass and fail, a controlled
   environment we can seed with known bugs, runs in the background by nature, real business pain, strong engineering story
   (agent loop, safety, supervision, evaluation), and it reuses the earlier work.
4. **Pause the project.** Valid, but forfeits the evaluation method and plumbing already built.

## Decision

**We will build option 3**, staged by releases with measured gates (roadmap): R1 local command-line agent against a seeded-bug
test bed with a **frozen pass bar**; R2 MCP supervision; R3 resilience and replay; R4 exploratory testing; R5 service mode on
demand; R6 beyond the web. "Full manual testing" is the long-term direction, not a promise; the claim is "automates the
routine, repeatable part and says clearly when it cannot decide".

What carries over: the evaluation method and harness; the provider-neutral model access, fallback and error classification;
the stateless-server and bring-your-own-key principles; the pointing model as the future vision fallback. What does not:
the desktop overlay interface, the demo quotas and the device caps.

**Legacy code (`backend/`, `client/`):** kept and tested until R1.0 is complete; then tagged `legacy-v1.1` and removed from the
main line, with the reusable pieces (model access, error classification, evaluation tools) extracted into the new package.
(The final choice is open question OQ-03.)

## Consequences

- A larger and riskier scope than the previous product; mitigated by gates with kill criteria (the R1.1 spike must meet or
  nearly meet the frozen bar before more is built).
- The product name no longer fits (OQ-01).
- Value to the owner shifts to the engineering story and a tool they can use on their own projects, more than to a consumer
  product. This is acceptable and stated.
- Competitive claims must be limited to what is measured; positioning is "measured, supervisable, local-first, honest verdicts",
  not "better than the incumbents".
- Documentation and process get heavier up front (ADR-0010) in exchange for recoverability.

## How we will know it was right

R1 exit gate (evaluation strategy section 5): correct pass at least 90%, bugs caught at least 80% with false pass at most 15%,
UI-change robustness at least 80%, repeatability at least 90%, zero safety-canary failures, median test at most 3 minutes.
If the spike (R1.1) misses a bar by more than 10 points and one structured mitigation also fails, we stop and write a new ADR
instead of continuing to build. A review point is also held if R1 has consumed 40 focused days without passing.
