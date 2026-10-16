# Contributing

Everything about how we work is in [`AGENTS.md`](AGENTS.md): the working agreement (humans and AI agents alike), cold-start
steps, commands, and the end-of-session protocol. Please read it before opening a pull request.

In short: branch from `v1.1`, keep changes small and focused, write tests and update the documentation in the same pull
request, use Conventional Commits, and make sure the checks pass (`python tools/check_docs.py` and the test commands in
`AGENTS.md` section 4). A decision that is hard to reverse needs an ADR (`docs/templates/adr-template.md`).
