# Engineering handbook

Status: Draft v0.1. How work is planned, written, reviewed, released and kept honest. It applies to humans and to AI
agents equally; agent-specific rules are in [`AGENTS.md`](../../AGENTS.md). Pipelines are in [CI/CD](ci-cd.md);
how documentation stays true is in the [documentation and memory policy](documentation-and-memory-policy.md).

Professional does not mean everything on day one. Practices below are tagged **[now]** (adopt at R0), **[R1]** or
**[later]** so the process grows with the project and nothing is theatre.

## 1. Principles

1. **Main is always releasable.** If it is not green, fixing it is the only priority.
2. **Small, reversible changes.** One concern per branch, per commit, per pull request.
3. **Evidence over assertion.** A change is done when its checks passed and its behaviour was seen, not when it was written.
4. **Decisions are written down** (ADRs), measurements are pre-registered, and both survive the people who made them.
5. **Automate what can be checked mechanically; review what needs judgement.**

## 2. Branching and merging [now]

- **Trunk-based development.** `main` is the only long-lived branch and is protected. Work happens on short-lived branches
  (ideally under three days) cut from `main` and merged back by pull request.
- **Branch names:** `type/short-description` where type is `feat`, `fix`, `docs`, `refactor`, `test`, `ci`, `chore`, or
  `exp` (an experiment with a pre-registration). Examples: `feat/event-store`, `docs/plan-v0.1`, `exp/r1-pass-bar`.
- **Merge method:** **squash merge** only, so `main` has one commit per pull request and a linear history. The pull-request
  title becomes the commit message and must follow Conventional Commits.
- **Retire long-lived branches.** The earlier `v1.1` integration branch is replaced by tagging its final state
  (`legacy-v1.1`) and continuing from `main`; this is part of accepting ADR-0009.
- **Releases are tags on `main`** (section 8). There is no `develop` branch.

## 3. Commits [now]

[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): summary`, imperative mood, under about 72
characters, with a body that explains **why** when it is not obvious.

- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `chore`, `revert`.
- Scopes (extend as needed): `domain`, `engine`, `agent`, `browser`, `safety`, `llm`, `store`, `reporting`, `mcp`, `cli`,
  `rest`, `testapp`, `suites`, `evals`, `docs`, `ci`, `deps`.
- Breaking change: `feat(cli)!: ...` and a `BREAKING CHANGE:` footer describing the migration.
- AI-assisted commits end with the agent's co-author trailer, so authorship is honest.
- Never commit secrets, private data, large binaries or generated output (check `git status` and `git diff --staged`).

## 4. Pull requests and review

**Every change goes through a pull request, including the owner's own and an agent's** [now].

- **Size:** aim for under about 400 changed lines; larger changes need a note explaining why they cannot be split.
- **Template:** `.github/PULL_REQUEST_TEMPLATE.md` asks for: what and why, linked issue (`Closes #n`), how it was verified,
  risk and rollback, and the **Docs impact** checklist (STATUS, ADR, requirements, changelog).
- **Draft** pull requests for work in progress; ready for review only when CI is green.
- **Checks that must pass to merge:** lint, types, tests, docs check, and (from Tier 1) code scanning and dependency
  review. See [CI/CD](ci-cd.md) for the exact list.
- **Review.** A solo project cannot honestly require a second human on every change, so the rule is layered:
  1. the author's self-review using the checklist below, always;
  2. an independent automated review (a second AI pass or code-scanning) on every non-trivial change;
  3. a human reviewer (a friend or mentor) for anything that touches **security, policy, the public interfaces or an ADR**.
  Required approvals are set to 0 while there is one maintainer and 1 as soon as there are two [R1].
- **Review checklist:** Does it do what the issue says and nothing else? Are tests added for behaviour, including failure
  cases? Were error and timeout paths considered? Any secret, log or artifact that could leak data? Is the documentation
  updated in this same pull request? Is it reversible?
- **Conversations resolved before merge**; the author merges after green.
- **Code owners:** `.github/CODEOWNERS` routes security-sensitive paths (`safety/`, `interfaces/`, `.github/`) to the owner.

## 5. Planning and issue tracking [now]

- **GitHub Issues are the backlog**; a **Project board** (Backlog, Ready, In progress, In review, Done) shows flow.
- **Issue types** (templates in `.github/ISSUE_TEMPLATE/`): *feature or story* (with acceptance criteria linked to requirement
  ids), *bug* (with reproduction and expected versus actual), *spike* (a question, a time box, and the decision it feeds),
  *decision* (an ADR to be written), *chore*.
- **Labels:** `type:*` (feature, bug, spike, chore, decision), `area:*` (domain, engine, agent, browser, safety, llm, store,
  reporting, mcp, cli, rest, testapp, evals, docs, ci), `priority:P0` to `P3`, `release:R1` to `R6`, `good-first-task`.
- **Milestones = releases** (R1 and so on). The milestone description is the exit gate from the roadmap.
- **Epics** are issues that link their child issues; each release has one.
- **Definition of Ready:** has a goal, acceptance criteria that name requirement ids, a size under about two days (else split),
  and any needed decision already made or scheduled.
- **Spikes** are time-boxed (a stated number of hours), end with a written answer (in the issue and, if it decides something,
  an ADR), and never leave behind unreviewed production code.

## 6. Definition of Done [now]

A change is done when **all** hold:

- [ ] Behaviour verified: automated tests for the logic *and* the failure paths, plus one real exercise of anything with I/O.
- [ ] Lint, types and the docs check pass locally and in CI.
- [ ] Requirements, design docs, interfaces and `CHANGELOG.md` updated in the same pull request where they are affected.
- [ ] Any decision recorded as an ADR; any new lesson in `lessons-learned.md`.
- [ ] `docs/status/STATUS.md` reflects the new state and the next step.
- [ ] No secret, private data or stray file in the diff; dependencies justified.
- [ ] A way to undo it is known (revert, flag, or migration back).

## 7. Code standards [R1 for the new package; the legacy code keeps its current rules]

- **Python 3.12+.** Formatting and linting with ruff; type-checking with mypy in strict mode for the core packages; the
  adapters are type-checked at a lower strictness and ratcheted up.
- **Tests:** pytest; names carry the requirement id (`test_fr_21_...`); markers `unit`, `contract`, `property`, `faults`, `e2e`,
  `eval`; no real network or model in unit and contract tests; deterministic (seeded) property tests; coverage for the core at
  least 80%, ratcheted upwards and never allowed to fall.
- **Design rules:** the dependency rule in the [LLD](../04-architecture/lld.md) (enforced by a test); pure functions for logic,
  I/O at the edges; explicit timeouts; no global mutable state; configuration validated at start.
- **Logging and errors:** structured logs with `run_id`; the error taxonomy of the LLD; never `except Exception: pass`.
- **Dependencies:** pinned and locked; adding one needs a sentence in the pull request on why it is needed and what was
  considered instead; licences checked; updated by Dependabot weekly with CI as the safety net.
- **Secrets:** environment or keyring only; `.env` ignored; `.env.example` lists the names and nothing else.

## 8. Versioning and releases

- **Semantic Versioning.** `0.y.z` until R2 is stable (public interfaces may change with a changelog entry), `1.0.0` when the
  CLI, MCP tools and event schema are declared stable.
- **Changelog:** [Keep a Changelog](https://keepachangelog.com/) format in `CHANGELOG.md`; generated from Conventional Commits
  by a release tool (release-please) from Tier 2, with a human-written highlights paragraph.
- **Release checklist** (`release` issue template): exit gate evidence attached; all CI green on the release commit; security
  checks of the [threat model](../04-architecture/security-threat-model.md) section 6; evaluation run recorded; cold-start
  drill passed and logged; `STATUS.md` and the roadmap updated; tag `vX.Y.Z` pushed; release notes published; artifacts
  (package, later container image) built **from the tag by CI**, never from a laptop.
- **Hotfix:** fix on a branch from `main`, merge by pull request, release a patch version. There are no separate hotfix branches.
- **Deprecation:** announce in the changelog and in output for at least one minor release before removal (NFR-14).

## 9. GitHub repository settings (checklist; not versioned by git, so re-apply after any loss)

**General:** default branch `main`; squash merging only; "automatically delete head branches" on; allow auto-merge; issues and
projects on; discussions off; wikis off (documentation lives in the repository).

**Branch protection or ruleset for `main`:** require a pull request; require status checks (see CI/CD for the exact job
names) and require branches to be up to date; require conversation resolution; require linear history; block force pushes
and branch deletion; **do not allow bypass**, even for the owner (the habit matters more than the speed). Tag protection
for `v*`.

**Security (Settings, Code security):** Dependabot alerts and security updates on; **secret scanning with push protection**
on; code scanning (CodeQL) on; private vulnerability reporting on; `SECURITY.md` present.

**Actions:** default workflow token permissions **read-only** (jobs request more explicitly); allow only GitHub-owned and
verified actions, **pinned by commit SHA**; require approval for workflows from first-time contributors.

**Environments (from Tier 3):** `staging` and `production`, each with required reviewers, secrets stored only on the
environment, and a wait timer on production.

**Labels and project board:** created from the taxonomy in section 5 (a script, `tools/`, will recreate them).

Keep a dated export of the settings (screenshots or `gh api` output) under `docs/runbooks/` when they change, so a lost
configuration can be rebuilt from the repository.

## 10. Working rhythm

| When | What |
|---|---|
| Start of a session | Read `docs/status/STATUS.md`; confirm the next step is still right |
| During | Small commits, tests with the code, notes for the handoff as you go |
| End of a session | End-of-session protocol in `AGENTS.md` (STATUS, ADRs, handoff, commit) |
| Weekly | Triage issues; refresh the roadmap if reality changed; skim CI health and flaky tests |
| Each release | Retrospective (one page in `docs/status/retros/`), cold-start drill, security checklist, update estimates |

## 11. Health metrics (reviewed monthly, not worshipped)

Lead time from first commit to merge; CI duration (target at most 10 minutes for a pull request); flaky-test count (target
zero in the required set; a flaky test is quarantined and an issue filed within 24 hours); change failure rate (releases needing
a patch); documentation drift (cold-start drill findings); evaluation trend (correct-pass, false-pass, cost per run).
