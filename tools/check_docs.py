"""Mechanical checks for the documentation system (see docs/06-process/documentation-and-memory-policy.md, section 8).

    python tools/check_docs.py            # check the repository this file lives in
    python tools/check_docs.py --root X   # check another tree (used by the tests)

Exit code 0 when everything is fine, 1 when problems were found. Warnings never fail the run. Standard library only, so
it runs anywhere without installing anything.
"""
import argparse
import datetime as dt
import re
import sys
from collections import deque
from pathlib import Path

ADR_STATUSES = ("Proposed", "Accepted", "Superseded", "Rejected", "Deprecated")
STATUS_HEADINGS = ("## Current phase", "## Exact next step", "## Open questions")
AGENTS_SECTIONS = ("Cold start", "Working agreement", "Commands", "Documentation duties", "End-of-session protocol")
MERMAID_STARTS = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "erDiagram", "classDiagram", "gantt", "journey", "pie")
STALE_AFTER_DAYS = 14

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCE = "```"


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.warnings: list[str] = []

    def problem(self, path: Path | str, message: str) -> None:
        self.problems.append(f"{path}: {message}")

    def warn(self, path: Path | str, message: str) -> None:
        self.warnings.append(f"{path}: {message}")


def strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code, so example links and snippets are not treated as real ones."""
    kept, inside = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(FENCE):
            inside = not inside
            continue
        if not inside:
            kept.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(kept)


def links_in(path: Path) -> list[str]:
    targets = []
    for raw in LINK.findall(strip_code(path.read_text(encoding="utf-8"))):
        target = raw.strip().split()[0] if raw.strip() else ""
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target.split("#")[0])
    return [t for t in targets if t]


def markdown_files(root: Path) -> list[Path]:
    files = list((root / "docs").rglob("*.md"))
    top_level = ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md")
    files += [root / name for name in top_level if (root / name).exists()]
    return sorted(set(files))


def check_links(root: Path, report: Report) -> None:
    for md in markdown_files(root):
        for target in links_in(md):
            if not (md.parent / target).resolve().exists():
                report.problem(md.relative_to(root), f"broken link: {target}")


def check_orphans(root: Path, report: Report) -> None:
    start = root / "docs" / "00-START-HERE.md"
    if not start.exists():
        report.problem("docs/00-START-HERE.md", "missing (the entry point of the documentation)")
        return
    seen, queue = {start.resolve()}, deque([start])
    while queue:
        current = queue.popleft()
        for target in links_in(current):
            candidate = (current.parent / target).resolve()
            if candidate.suffix == ".md" and candidate.exists() and candidate not in seen:
                seen.add(candidate)
                queue.append(candidate)
    for md in (root / "docs").rglob("*.md"):
        if md.resolve() not in seen:
            report.problem(md.relative_to(root), "orphan document: not reachable from docs/00-START-HERE.md through links")


def adr_files(root: Path) -> list[Path]:
    folder = root / "docs" / "decisions"
    return sorted(p for p in folder.glob("[0-9][0-9][0-9][0-9]-*.md")) if folder.exists() else []


def check_adrs(root: Path, report: Report, today: dt.date) -> None:
    files = adr_files(root)
    index = root / "docs" / "decisions" / "README.md"
    if not index.exists():
        report.problem("docs/decisions/README.md", "missing decision index")
        return
    numbers = [int(p.name[:4]) for p in files]
    if numbers != list(range(1, len(numbers) + 1)):
        report.problem("docs/decisions", f"ADR numbers must be contiguous from 0001, found {numbers}")

    statuses: dict[str, str] = {}
    for path in files:
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8")
        number = path.name[:4]
        heading = re.match(rf"# ADR-{number}: .+", text)
        if not heading:
            report.problem(rel, f"first line must be '# ADR-{number}: <title>'")
        status = re.search(r"(?m)^- Status: (\w+)", text)
        if not status or status.group(1) not in ADR_STATUSES:
            report.problem(rel, f"needs a line '- Status: <one of {', '.join(ADR_STATUSES)}>'")
        else:
            statuses[path.name] = status.group(1)
        date = re.search(r"(?m)^- Date: (\d{4}-\d{2}-\d{2})\s*$", text)
        if not date:
            report.problem(rel, "needs a line '- Date: YYYY-MM-DD'")
        else:
            try:
                if dt.date.fromisoformat(date.group(1)) > today:
                    report.problem(rel, f"date {date.group(1)} is in the future (use the system date)")
            except ValueError:
                report.problem(rel, f"invalid date {date.group(1)}")

    rows = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        row = re.match(r"\|\s*\[ADR-\d{4}\]\(([^)]+\.md)\)\s*\|[^|]*\|\s*(\w+)\s*\|", line)
        if row:
            rows[row.group(1)] = row.group(2)
    for name in statuses:
        if name not in rows:
            report.problem("docs/decisions/README.md", f"index has no row for {name}")
        elif rows[name] != statuses[name]:
            report.problem("docs/decisions/README.md", f"index says {name} is {rows[name]}, the file says {statuses[name]}")
    for name in rows:
        if not (root / "docs" / "decisions" / name).exists():
            report.problem("docs/decisions/README.md", f"index row points to a missing file {name}")


def check_status(root: Path, report: Report, today: dt.date) -> None:
    path = root / "docs" / "status" / "STATUS.md"
    rel = "docs/status/STATUS.md"
    if not path.exists():
        report.problem(rel, "missing: the single place that says where the project is now")
        return
    text = path.read_text(encoding="utf-8")
    for heading in STATUS_HEADINGS:
        if heading not in text:
            report.problem(rel, f"missing required heading '{heading}'")
    date = re.search(r"(?m)^Last updated: (\d{4}-\d{2}-\d{2})\s*$", text)
    if not date:
        report.problem(rel, "needs a line 'Last updated: YYYY-MM-DD'")
        return
    try:
        updated = dt.date.fromisoformat(date.group(1))
    except ValueError:
        report.problem(rel, f"invalid date {date.group(1)}")
        return
    if updated > today:
        report.problem(rel, f"'Last updated' {updated} is in the future")
    elif (today - updated).days > STALE_AFTER_DAYS:
        report.warn(rel, f"not updated for {(today - updated).days} days (limit {STALE_AFTER_DAYS}); is it still true?")


def check_agent_files(root: Path, report: Report) -> None:
    agents = root / "AGENTS.md"
    if not agents.exists():
        report.problem("AGENTS.md", "missing: the entry point for AI agents")
    else:
        text = agents.read_text(encoding="utf-8")
        for section in AGENTS_SECTIONS:
            if not re.search(rf"(?mi)^#+ .*{re.escape(section)}", text):
                report.problem("AGENTS.md", f"missing a section about '{section}'")
    claude = root / "CLAUDE.md"
    if not claude.exists():
        report.problem("CLAUDE.md", "missing (it must import AGENTS.md)")
    else:
        first = next((ln.strip() for ln in claude.read_text(encoding="utf-8").splitlines() if ln.strip()), "")
        if first != "@AGENTS.md":
            report.problem("CLAUDE.md", "first non-empty line must be '@AGENTS.md' so there is one source of truth")


def check_mermaid(root: Path, report: Report) -> None:
    for md in markdown_files(root):
        inside, block, start_line = False, [], 0
        for number, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(FENCE + "mermaid"):
                inside, block, start_line = True, [], number
            elif inside and stripped.startswith(FENCE):
                inside = False
                body = "\n".join(block).strip()
                if not body or not body.startswith(MERMAID_STARTS):
                    report.problem(
                        md.relative_to(root),
                        f"mermaid block at line {start_line} is empty or starts with an unknown diagram type",
                    )
            elif inside:
                block.append(line)
        if inside:
            report.problem(md.relative_to(root), f"mermaid block at line {start_line} is not closed")


REFERENCE_KINDS = (
    # (label, pattern of a reference, definition document, pattern of a definition row)
    ("requirement", r"\b(?:N?FR)-\d{2}\b", "docs/02-requirements.md", r"(?m)^\|\s*((?:N?FR)-\d{2})\s*\|"),
    ("open question", r"\bOQ-\d{2}\b", "docs/07-open-questions.md", r"(?m)^\|\s*(OQ-\d{2})\s*\|"),
    ("lesson", r"\bL-\d{2}\b", "docs/06-process/lessons-learned.md", r"(?m)^\|\s*(L-\d{2})\s*\|"),
)
DECISION_REFERENCE = r"\bADR-\d{4}\b"


def check_references(root: Path, report: Report) -> None:
    """Every id mentioned anywhere must be defined in its home document (no dangling FR-, ADR-, OQ-, L- references)."""
    definitions: dict[str, set[str] | None] = {}
    for label, _ref, doc, row in REFERENCE_KINDS:
        path = root / doc
        definitions[label] = set(re.findall(row, path.read_text(encoding="utf-8"))) if path.exists() else None
    definitions["decision"] = {f"ADR-{p.name[:4]}" for p in adr_files(root)}
    patterns = {label: ref for label, ref, _doc, _row in REFERENCE_KINDS}
    patterns["decision"] = DECISION_REFERENCE
    homes = {label: doc for label, _ref, doc, _row in REFERENCE_KINDS}
    homes["decision"] = "docs/decisions"
    for md in markdown_files(root):
        text = strip_code(md.read_text(encoding="utf-8"))
        for label, pattern in patterns.items():
            for found in sorted(set(re.findall(pattern, text))):
                defined = definitions[label]
                if defined is None:
                    report.problem(md.relative_to(root), f"mentions {found} but its home document {homes[label]} does not exist")
                elif found not in defined:
                    report.problem(md.relative_to(root), f"reference to undefined {label} {found} (not defined in {homes[label]})")


def run_checks(root: Path, today: dt.date | None = None) -> Report:
    today = today or dt.date.today()
    report = Report()
    check_agent_files(root, report)
    check_adrs(root, report, today)
    check_status(root, report, today)
    check_links(root, report)
    check_orphans(root, report)
    check_references(root, report)
    check_mermaid(root, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="repository root to check")
    args = parser.parse_args()
    report = run_checks(Path(args.root))
    for warning in report.warnings:
        print(f"WARNING {warning}")
    for problem in report.problems:
        print(f"ERROR   {problem}")
    if report.problems:
        print(f"\n{len(report.problems)} problem(s) found. See docs/06-process/documentation-and-memory-policy.md section 8.")
        return 1
    print(f"docs check passed ({len(report.warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
