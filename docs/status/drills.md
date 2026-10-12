# Cold-start drill log

Status: living document. Procedure: [documentation and memory policy](../06-process/documentation-and-memory-policy.md)
section 7. Record every drill here, including failures; a drill that found gaps is a success.

| Date | Commit | Agent and setup | Result (six answers, small task) | Gaps found and fixed |
|---|---|---|---|---|
| 2026-10-12 | `docs/plan-v0.1` (uncommitted) | **Author's own cold read, not independent, does not count** | Answers a to f derivable from the documents; the exact next step was clear | Found and fixed: STATUS used an obsolete step name (P0) and a vague link; **the work was not pushed to GitHub, so a clone would not contain it** (now the first item in STATUS and a step in the end-of-session protocol) |
| (pending) | | **Independent fresh agent: required for the R0 exit gate** | | |

## Questions asked (so results are comparable)

a. What is this project in three sentences? b. What is the current phase and the exact next step? c. Name three decisions in force
and why. d. How do I run the tests and the docs check? e. What is not in the repository, and how is it recovered? f. Which release
gate are we working toward and what does it require?

Small task variants (rotate): add a requirement; record a decision as an ADR and update the index; answer "what changed in
ADR-0008's status and why?"; add a lesson; update STATUS after a pretend session.
