# Changelog

All notable user-visible changes are recorded here, newest first, in the
[Keep a Changelog](https://keepachangelog.com/) format. The project follows
[Semantic Versioning](https://semver.org/); see `docs/06-process/engineering-handbook.md` section 8.

## [Unreleased]

### Added
- Project plan v0.1: vision, requirements, high- and low-level design, security model, scaling design, evaluation
  strategy, engineering and CI/CD process, decision log (ADR-0009 to ADR-0013 proposed) under `docs/`.
- `AGENTS.md` and `CLAUDE.md`: the working agreement for AI agents and the cold-start procedure.
- `tools/check_docs.py`: mechanical documentation checks, run in CI.
- GitHub issue and pull-request templates, code owners and Dependabot configuration.

### Changed
- The single decision-log file was split into one file per decision under `docs/decisions/`.
- ADR-0008 date corrected to 2026-10-12.

(Releases before the plan are the earlier overlay product and are not versioned retroactively.)
