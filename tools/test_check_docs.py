import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import check_docs  # noqa: E402

TODAY = dt.date(2026, 10, 12)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


AGENTS = """# AGENTS.md
## 1. Cold start
## 3. Working agreement
## 4. Commands
## 5. Documentation duties
## 6. End-of-session protocol
"""

STATUS = """# Project status

Last updated: 2026-10-10

## Current phase
x
## Exact next step
y
## Open questions
z
"""

ADR_1 = "# ADR-0001: First\n\n- Status: Accepted\n- Date: 2026-10-01\n\nbody\n"
ADR_2 = "# ADR-0002: Second\n\n- Status: Proposed\n- Date: 2026-10-02\n\nbody\n"
INDEX = """# Decision log

| ADR | Decision | Status | Date |
|---|---|---|---|
| [ADR-0001](0001-first.md) | First | Accepted | 2026-10-01 |
| [ADR-0002](0002-second.md) | Second | Proposed | 2026-10-02 |
"""
START = """# Start

[status](status/STATUS.md) [decisions](decisions/README.md) [other](other.md)
"""


@pytest.fixture
def repo(tmp_path):
    write(tmp_path, "AGENTS.md", AGENTS)
    write(tmp_path, "CLAUDE.md", "@AGENTS.md\n\nmore\n")
    write(tmp_path, "docs/00-START-HERE.md", START)
    write(tmp_path, "docs/other.md", "# Other\n")
    write(tmp_path, "docs/status/STATUS.md", STATUS)
    write(tmp_path, "docs/decisions/README.md", INDEX)
    write(tmp_path, "docs/decisions/0001-first.md", ADR_1)
    write(tmp_path, "docs/decisions/0002-second.md", ADR_2)
    return tmp_path


def problems(root):
    return check_docs.run_checks(root, TODAY).problems


def warnings(root):
    return check_docs.run_checks(root, TODAY).warnings


def test_a_valid_tree_has_no_problems(repo):
    assert problems(repo) == []


def test_the_real_repository_passes():
    root = Path(__file__).resolve().parent.parent
    assert check_docs.run_checks(root, dt.date.today()).problems == []


# --- ADRs ------------------------------------------------------------------------------------------------------

def test_adr_missing_from_the_index_is_reported(repo):
    write(repo, "docs/decisions/README.md", INDEX.replace("| [ADR-0002](0002-second.md) | Second | Proposed | 2026-10-02 |\n", ""))
    assert any("no row for 0002-second.md" in p for p in problems(repo))


def test_index_status_that_disagrees_with_the_file_is_reported(repo):
    write(repo, "docs/decisions/README.md", INDEX.replace("| Second | Proposed", "| Second | Accepted"))
    assert any("index says 0002-second.md is Accepted" in p for p in problems(repo))


def test_index_row_pointing_at_a_missing_file_is_reported(repo):
    write(repo, "docs/decisions/README.md", INDEX + "| [ADR-0003](0003-ghost.md) | Ghost | Accepted | 2026-10-03 |\n")
    assert any("missing file 0003-ghost.md" in p for p in problems(repo))


def test_gap_in_adr_numbering_is_reported(repo):
    (repo / "docs/decisions/0002-second.md").rename(repo / "docs/decisions/0003-second.md")
    assert any("contiguous" in p for p in problems(repo))


@pytest.mark.parametrize("bad", ["- Status: Maybe\n", ""])
def test_adr_with_an_invalid_or_missing_status_is_reported(repo, bad):
    write(repo, "docs/decisions/0002-second.md", "# ADR-0002: Second\n\n" + bad + "- Date: 2026-10-02\n")
    assert any("needs a line '- Status:" in p for p in problems(repo))


def test_adr_dated_in_the_future_is_reported(repo):
    write(repo, "docs/decisions/0002-second.md", ADR_2.replace("2026-10-02", "2027-01-01"))
    assert any("in the future" in p for p in problems(repo))


def test_adr_heading_must_match_its_file_number(repo):
    write(repo, "docs/decisions/0002-second.md", ADR_2.replace("ADR-0002", "ADR-0009"))
    assert any("first line must be" in p for p in problems(repo))


# --- status file -----------------------------------------------------------------------------------------------

def test_status_missing_heading_is_reported(repo):
    write(repo, "docs/status/STATUS.md", STATUS.replace("## Exact next step\ny\n", ""))
    assert any("Exact next step" in p for p in problems(repo))


def test_status_in_the_future_is_an_error_and_stale_is_only_a_warning(repo):
    write(repo, "docs/status/STATUS.md", STATUS.replace("2026-10-10", "2026-11-01"))
    assert any("in the future" in p for p in problems(repo))
    write(repo, "docs/status/STATUS.md", STATUS.replace("2026-10-10", "2026-09-01"))
    assert problems(repo) == []
    assert any("not updated for" in w for w in warnings(repo))


def test_status_without_a_date_is_reported(repo):
    write(repo, "docs/status/STATUS.md", STATUS.replace("Last updated: 2026-10-10", "Updated recently"))
    assert any("Last updated" in p for p in problems(repo))


# --- links and orphans ----------------------------------------------------------------------------------------

def test_broken_internal_link_is_reported(repo):
    write(repo, "docs/other.md", "# Other\n\nsee [nothing](nope.md)\n")
    assert any("broken link: nope.md" in p for p in problems(repo))


def test_links_in_code_and_external_links_are_ignored(repo):
    write(repo, "docs/other.md", "# Other\n\n`[x](nope.md)`\n\n```\n[y](nope2.md)\n```\n\n[web](https://example.com/a) [anchor](#top)\n")
    assert problems(repo) == []


def test_link_with_an_anchor_checks_the_file_only(repo):
    write(repo, "docs/other.md", "# Other\n\n[ok](status/STATUS.md#current-phase)\n")
    assert problems(repo) == []


def test_orphan_document_is_reported(repo):
    write(repo, "docs/lonely.md", "# Lonely\n")
    assert any("orphan document" in p and "lonely.md" in p for p in problems(repo))


def test_a_document_reachable_only_through_another_is_not_an_orphan(repo):
    write(repo, "docs/other.md", "# Other\n\n[deeper](deeper/x.md)\n")
    write(repo, "docs/deeper/x.md", "# X\n")
    assert problems(repo) == []


# --- agent files and mermaid ----------------------------------------------------------------------------------

def test_agents_file_missing_a_required_section_is_reported(repo):
    write(repo, "AGENTS.md", AGENTS.replace("## 4. Commands\n", ""))
    assert any("Commands" in p for p in problems(repo))


def test_claude_file_must_import_agents(repo):
    write(repo, "CLAUDE.md", "# Own rules\n")
    assert any("@AGENTS.md" in p for p in problems(repo))


def test_mermaid_blocks_are_sanity_checked(repo):
    write(repo, "docs/other.md", "# Other\n\n```mermaid\nflowchart LR\n  a --> b\n```\n")
    assert problems(repo) == []
    write(repo, "docs/other.md", "# Other\n\n```mermaid\n\n```\n")
    assert any("mermaid block" in p for p in problems(repo))
    write(repo, "docs/other.md", "# Other\n\n```mermaid\nnonsense here\n```\n")
    assert any("unknown diagram type" in p for p in problems(repo))
    write(repo, "docs/other.md", "# Other\n\n```mermaid\nflowchart LR\n")
    assert any("not closed" in p for p in problems(repo))


# --- references ----------------------------------------------------------------------------------------------

def add_definitions(repo):
    write(repo, "docs/02-requirements.md", "# Requirements\n\n| ID | R |\n|---|---|\n| FR-01 | a |\n| NFR-02 | b |\n")
    write(repo, "docs/07-open-questions.md", "# Questions\n\n| ID | Q |\n|---|---|\n| OQ-01 | a |\n")
    write(repo, "docs/06-process/lessons-learned.md", "# Lessons\n\n| # | x |\n|---|---|\n| L-01 | a |\n")
    write(repo, "docs/00-START-HERE.md", START + "\n[r](02-requirements.md) [q](07-open-questions.md) [l](06-process/lessons-learned.md)\n")


def test_defined_references_pass(repo):
    add_definitions(repo)
    write(repo, "docs/other.md", "# Other\n\nSee FR-01, NFR-02, ADR-0001, OQ-01 and L-01.\n")
    assert problems(repo) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("FR-09", "undefined requirement FR-09"),
        ("NFR-77", "undefined requirement NFR-77"),
        ("ADR-0042", "undefined decision ADR-0042"),
        ("OQ-30", "undefined open question OQ-30"),
        ("L-99", "undefined lesson L-99"),
    ],
)
def test_dangling_references_are_reported(repo, text, expected):
    add_definitions(repo)
    write(repo, "docs/other.md", f"# Other\n\nThis mentions {text}.\n")
    assert any(expected in p for p in problems(repo))


def test_references_inside_code_are_not_checked(repo):
    add_definitions(repo)
    write(repo, "docs/other.md", "# Other\n\nExample: `FR-99` and\n\n```\nADR-0099\n```\n")
    assert problems(repo) == []


def test_ids_inside_longer_words_are_not_mistaken_for_references(repo):
    add_definitions(repo)
    write(repo, "docs/other.md", "# Other\n\nTHE-FULL-12 and SEL-77 are just words, but FR-01 is real.\n")
    assert problems(repo) == []


def test_a_reference_without_its_home_document_is_reported(repo):
    write(repo, "docs/other.md", "# Other\n\nSee FR-01.\n")
    assert any("home document docs/02-requirements.md does not exist" in p for p in problems(repo))


def test_command_line_exit_codes_and_output(repo, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["check_docs.py", "--root", str(repo)])
    assert check_docs.main() == 0
    assert "docs check passed" in capsys.readouterr().out

    write(repo, "docs/other.md", "# Other\n\n[bad](missing.md)\n")
    assert check_docs.main() == 1
    output = capsys.readouterr().out
    assert "ERROR" in output and "broken link: missing.md" in output and "1 problem(s) found" in output
