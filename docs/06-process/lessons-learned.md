# Lessons learned

Status: living document. Each entry is a mistake or surprise that already cost time, with the rule that prevents a repeat.
Add an entry whenever something cost more than about 30 minutes or could have caused harm. Format: **what happened, why, the
rule**. Dates are when it was found.

## Tooling and environment (Windows, Git Bash, PowerShell)

| # | What happened | Why | Rule |
|---|---|---|---|
| L-01 | Regexes and `\n` written inside shell heredocs came out wrong (real newlines, lost backslashes) | The shell and tool layers process backslashes | Write files with the editor tools, not heredocs, whenever text contains backslashes |
| L-02 | `pip install -r requirements.txt` failed with a "f a s t a p i" error | The `Write` tool **preserved the old file's UTF-16 encoding** when overwriting | Delete and recreate files that were created by `pip freeze` in PowerShell; check with `file` |
| L-03 | A migration script failed, yet the next line deleted the source file | The commands were on **separate lines**, so the second ran regardless | Chain with `&&` or use `set -e`; never delete before the replacement is verified. (Recovered from git: another reason to commit first.) |
| L-04 | `.venv/Scripts/python.exe: No such file` after `cd` | A relative interpreter path stops working after changing directory | Use paths relative to the repository root, or absolute |
| L-05 | A docker command failed and could not verify the build | Docker Desktop was not running | State clearly what is **unverified**; deployment verification is its own step |
| L-06 | A dependency install pulled a much newer `google-genai` than was pinned | A framework depended on a newer SDK | Test requirements in a **clean** virtual environment before committing them |

## Testing user interfaces

| # | What happened | Why | Rule |
|---|---|---|---|
| L-07 | The review page showed no images | The in-app preview loads local files as a `data:` page: no folder, no relative paths, no `localStorage` | Test pages the way users open them; ship a self-contained build; show a clear message when assets fail to load |
| L-08 | Tall screenshots overflowed the window; buttons sat below the fold; an image was shown at one-third size | Scripted events passed while real layout was never exercised; layout was measured once in JavaScript and an emulated window change fired no resize event | Test with a **real layout and real input**; size with CSS instead of measuring in JavaScript; probe element positions numerically at two window sizes |
| L-09 | Pages claimed "saved" when browser storage was blocked | Errors were swallowed silently | Never report success you did not observe; surface the failure |
| L-10 | The test harness mapped click coordinates inconsistently | An emulated viewport changed the screenshot frame | Calibrate with a known target first; read positions from the page, not from the picture |

## Evaluation and measurement

| # | What happened | Why | Rule |
|---|---|---|---|
| L-11 | A rule printed "GO" on 8 data points | The rule had no minimum sample size | Every verdict needs a minimum sample; below it, "insufficient data" |
| L-12 | The rule could pass with **no small targets** at all | A missing group was treated as "OK" instead of "unknown" | Test pass rules by feeding them a perfect model, a random model and a degenerate dataset; missing data is never a pass |
| L-13 | 60 labelled boxes covered a median 35% of the screen | Labellers drew regions; nothing flagged it; the labels were then useless for scoring | Show the **random-guess baseline**; warn at labelling time; inspect the label distribution before running |
| L-14 | "Model B is 5 times faster" reversed on the next run | Free-tier latency is mostly load noise; the sample was tiny | Do not draw conclusions from small timing samples; record date and conditions; re-measure on the real tier |
| L-15 | A test with mocks passed while the real call failed on the first try | The mock raised the wrong exception class; the real SDK used another family | At every integration boundary run **one live check, including a failure path**, before trusting mocks |
| L-16 | A results line appeared strong but hid the hard case | Easy targets (17 of 17) lifted the average | Break results down by the case the product depends on (here: small controls); report that number prominently |
| L-17 | A decision-log date was wrong by a day | A date was assumed instead of read | Use the system date (`date`) when recording dates |

## Process and safety

| # | What happened | Why | Rule |
|---|---|---|---|
| L-18 | The decision log was one growing file | Hard to diff and link | One ADR per file with an index and a status line each |
| L-19 | A VM SSH key and an obsolete OAuth secret sat in the project folder | Convenience | Keep keys **outside** the repository folder; revoke obsolete credentials; git-ignore is a safety net, not a plan |
| L-20 | Private screenshots could have been printed into logs and chats | They were the working data | Report counts and aggregates only; keep private data git-ignored and outside the transcript |
| L-21 | A long single instruction list was lost with the chat | Knowledge lived in the conversation | This documentation system: everything important is written into the repository |
| L-22 | A 5-minute estimate for a "quick" evaluation ran 30 minutes | Free-tier calls are slow and sequential | Estimate model-bound work from measured latency, run it in the background, report progress |

## Documentation and automation tooling

| # | What happened | Why | Rule |
|---|---|---|---|
| L-23 | A Mermaid diagram that looked fine in the source used the reserved word `graph` as a node name and would not render | Syntax cannot be judged by eye, and a script that only counts fences cannot see it | Parse every diagram with the real library (a throwaway page with `mermaid.parse`) whenever diagrams change |
| L-24 | A workflow file was rejected by the YAML parser | A step name contained `: ` (colon and space), read as a nested mapping | Validate every YAML file with a parser before committing; quote any scalar that contains a colon |
| L-25 | A docs checker passed on its first run | A checker that has never failed proves nothing | Write negative tests for every rule, and break a **copy of the real repository** to see each rule fire |
| L-26 | The same shell-escaping mistake as L-01 was made again while writing the checker: word-boundary escapes became invisible control characters and a test file was split across real newlines | A known rule was not applied under time pressure; the damage was invisible until a linter ran | Rules need teeth: write any file containing regexes or backslashes with the editor tools **and** scan it for control characters afterwards (`ord(c) < 32` other than newline and tab) |

## How to add a lesson

Append a row with the next `L-NN`, keep it to one line per column, and, if it implies a rule that tooling can enforce, open an
issue to enforce it. If a lesson changes how agents must behave, add one line to `AGENTS.md` section 7 as well.
