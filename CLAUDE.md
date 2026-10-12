@AGENTS.md

# Claude Code specifics

- `AGENTS.md` above is the single source of truth for how to work in this repository. Follow it exactly.
- Claude Code's auto-memory (under `~/.claude/projects/...`) is **local to one machine and not authoritative**. Use it
  only for short pointers; anything that matters goes into the repository docs (see AGENTS.md section 6).
- Prefer the dedicated file tools (Read, Write, Edit, Glob, Grep) over shell for reading and editing files.
- Run long or repeated checks in the background and report counts, not private content.
