# Open questions

Status: living document. Anything we do not yet know or have not yet decided that could change the work. Each has an
owner, a "needed by" point, and a default we will use if nobody decides. When answered, move the answer into the right
document (an ADR if it is a decision), mark the row *Closed*, and keep the row for history.

| ID | Question | Why it matters | Options and leaning | Decides | Needed by | Status |
|---|---|---|---|---|---|---|
| OQ-01 | **Product name.** "AskOverlay" described an overlay that no longer exists | Public name, package and command names, domain, repository | Pick a neutral descriptive name; check trademarks and domains. Working package name `testagent`, command `testagent` | Owner | R1 exit (before anything is published) | Open |
| OQ-02 | **Licence** | Determines who may use, copy and contribute; matters for the portfolio | Permissive (MIT or Apache-2.0) leaning Apache-2.0 for the patent grant; copyleft only with a reason | Owner | Before the first public release | Open |
| OQ-03 | **Fate of the legacy overlay code** (`backend/`, `client/`) | Repository clarity; maintenance burden | Leaning: keep until R1.0, then tag `legacy-v1.1`, extract reusable parts, remove from main | Owner | R1.0 | Open |
| OQ-04 | **Weekly time budget and target dates** | The roadmap has effort, not dates | Owner states hours per week; planning converts effort to calendar with a stated margin | Owner | R0 exit | Open |
| OQ-05 | **Which model provider(s) and budget** for the first measurements | Latency, cost and quota decide what R1 can show; free tiers are slow and rate-limited | Leaning: current Gemini lite models first (already integrated), a paid tier for the final bar run; keep the gateway provider-neutral | Owner | R1.0 | Open |
| OQ-06 | **Do prompts sent with a free-tier Gemini key get used by Google to improve its products?** | Privacy claims for any screenshots or page text; the security model assumes the provider sees them | Verify in the provider's current terms; until verified, claim nothing and prefer a paid tier for sensitive material | Owner (with a reviewer) | Before any privacy statement is published | Open |
| OQ-07 | **Who reviews, and how** | A solo project has no second reviewer; security-relevant changes need one | A named friend or mentor reviews security, policy and interface changes; an independent AI pass for the rest | Owner | R0 exit | Open |
| OQ-08 | **Browsers beyond Chromium** | Real users use more than Chromium | Chromium only for R1; Firefox and WebKit at R3 or later | Owner | R3 | Open (default set) |
| OQ-09 | **Test-file format** | Authoring comfort versus parsing simplicity | YAML for R1; Markdown with front matter later if wanted | Owner | R1.0 | Open (default set) |
| OQ-10 | **Python project tooling** (pip versus uv; lock files) | Reproducibility and CI speed | Spike at R1.0; choose one, record in an ADR | Owner with agent | R1.0 | Open |
| OQ-11 | **Where documentation is published** | Readability for outsiders | The repository on GitHub is enough for R1; consider static site generation later | Owner | R2 | Open (deferred) |
| OQ-12 | **Public or private repository, and history audit** | The repository may be shown to employers; history must hold no secrets | Audit history first (an earlier virtual environment was committed once; no secrets were found), remove stray files from the tree, then decide | Owner | Before making it public | Open |
| OQ-13 | **Technology of the test-bed web store** | It must resemble real sites: some server-rendered pages and some JavaScript-heavy ones | Leaning: a small FastAPI app with templates plus a few client-side pages; decide at R1.0 | Owner with agent | R1.0 | Open |
| OQ-14 | **Authentication flows with verification codes** | Real applications use them; they must not be automated carelessly | Out of scope for R1; later: approved test accounts and test-mode bypasses, never real inboxes | Owner | R3 or later | Open (default set) |
| OQ-15 | **Retention of the earlier evaluation data** (screenshots, labels, judgments) | Private data; needed only to regenerate or re-audit results | Keep a private encrypted backup outside the repository, or delete once the aggregates are recorded | Owner | R0 exit | Open |

Questions the owner asked to defer: all of the above were raised in review and intentionally **not** blocking the plan; they are
resolved at their "needed by" point.
