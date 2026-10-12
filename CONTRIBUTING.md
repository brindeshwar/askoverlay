# Contributing

Everything about how we work is in two places; please read them before opening a pull request:

1. [`AGENTS.md`](AGENTS.md): the working agreement (humans and AI agents alike), cold-start steps, commands, end-of-session protocol.
2. [`docs/06-process/engineering-handbook.md`](docs/06-process/engineering-handbook.md): branching, commits, pull requests,
   review, versioning and releases.

In short: branch from `main`, keep changes small and focused, write tests and update the documentation in the same pull
request, use Conventional Commits, and make sure the checks pass (`python tools/check_docs.py` and the test commands in
`AGENTS.md` section 4). A decision that is hard to reverse needs an ADR (`docs/templates/adr-template.md`).
