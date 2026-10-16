## What and why

<!-- One or two sentences: what changes, and why it is needed. Link the issue. -->

Closes #

## How it was verified

<!-- Paste the commands you ran and what they showed. "Not verified: X" is a fine and honest line. -->

- [ ] Tests for the logic **and** the failure paths (commands and results above)
- [ ] Exercised for real (anything with a user interface, a network call, or a browser)
- [ ] Lint, types and `python tools/check_docs.py` pass locally

## Risk and rollback

<!-- What could go wrong? How do we undo it (revert, flag, migration back)? -->

## Docs impact

- [ ] `docs/status/STATUS.md` updated (state and the exact next step)
- [ ] ADR added or its status changed, and the index updated (if a decision was made)
- [ ] Requirements, roadmap or design docs updated (if scope, behaviour or structure changed)
- [ ] `CHANGELOG.md` updated (if user-visible)
- [ ] `docs/06-process/lessons-learned.md` updated (if something cost time)
- [ ] None of the above applies, because: ...

## Checklist

- [ ] One concern per pull request; no unrelated changes
- [ ] No secrets, private data or stray files in the diff
- [ ] New dependencies justified in this description
- [ ] Commit messages follow Conventional Commits (the squash title will be used)
