# ADR-0011: The verdict is computed from recorded assertions, never from the model's opinion

- Status: Proposed
- Date: 2026-10-12
- Related: Implements FR-20 to FR-23; specified in the [LLD](../04-architecture/lld.md) section 6.

## Context

The worst failure of a testing tool is a **false pass**: reporting success while a defect exists. Language models tend to
agree that a task "went fine", can mistake a plausible page for a correct one, and may be steered by text on the page.
If the model decides the verdict, every error and every manipulation turns directly into a false pass.

## Options considered

1. **The model declares the verdict** ("did the test pass?"). Simple; most exposed to false passes and injection.
2. **The model declares it, a second model verifies.** More cost; correlated errors; still opinion on opinion.
3. **Compute the verdict from assertions that were actually executed and recorded with evidence**; the model proposes actions
   and assertions, but cannot finish a test as passed without coverage of the test's expectations.

## Decision

We will use option 3. Each test lists explicit `expect` items. The agent must execute at least one assertion for each; the
verdict engine (a pure function) returns **passed** only if every expectation has a passing assertion and nothing failed;
**failed** if any assertion failed; **inconclusive** if expectations were left unevaluated, a budget was hit or the run stalled;
**blocked** or **error** for approval and infrastructure outcomes. Assertions are *deterministic* (text, URL, element state,
count, attribute: evaluated by code) or *model-judged* (flagged in every report, and rejected in `strict` mode).

## Consequences

- More runs end *inconclusive* than a permissive design would; this is honest and visible, and the report says what was missing.
- Test authors must state expectations explicitly. This is good test practice and is what makes the result checkable.
- Quality now depends on the deterministic assertion set being expressive enough; the model-judged share is measured and
  reported as a trust indicator.
- The verdict function is simple enough to test exhaustively with property-based tests.
- A recorded failure is conclusive; there is no "retry until pass" in R1 (flake handling in R3 is explicit and labelled).

## How we will know it was right

The false-pass rate on seeded bugs is at most 15% at R1 and at most 10% at R3, reported separately and prominently; no run in the
evaluation or in property tests reaches `passed` without full assertion coverage.
