"""Turn your review judgments into the verdict.

    python review_report.py                       # latest run
    python review_report.py --run results/<run>

Reads <run>/review/judgments.json (exported from the review page), <run>/review/key.json and <run>/results.json.
A model that failed to give a usable answer counts as wrong rather than being dropped. Prints only aggregates.
"""
import argparse
import json
import os
import sys

import review
import scoring


def pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def interval(ci) -> str:
    return "" if ci is None else f" (plausibly {ci[0] * 100:.0f}-{ci[1] * 100:.0f}%)"


def collect_items(run_dir: str) -> list[dict]:
    review_dir = os.path.join(run_dir, "review")
    with open(os.path.join(review_dir, "judgments.json"), encoding="utf-8") as f:
        judgments = json.load(f)["judgments"]
    with open(os.path.join(review_dir, "key.json"), encoding="utf-8") as f:
        key = json.load(f)
    with open(os.path.join(run_dir, "results.json"), encoding="utf-8") as f:
        records = json.load(f)

    items = []
    for item_id, info in key.items():
        value = judgments.get(item_id)
        items.append({"model": info["model"], "judgment": value if value in (1, 2, 3) else None,
                      "button_sized": info["button_sized"]})
    for r in records:           # no usable answer: the model failed, which is a wrong answer
        if not r["pred"]:
            items.append({"model": r["model"], "judgment": "fail", "button_sized": False})
    return items


def report(run_dir: str) -> str:
    summary = scoring.judged_summary(collect_items(run_dir))
    lines = ["# Human-judged pointing accuracy", ""]
    for model, s in summary.items():
        lines += [
            f"## {model}",
            "",
            f"- judged answers counted: {s['total']} (including {s['failures']} with no usable answer, counted as wrong; "
            f"{s['skipped']} not judged or skipped)",
            f"- on the right control: **{pct(s['right'])}**{interval(s['right_ci'])}",
            f"- right control AND tight box: **{pct(s['tight'])}**{interval(s['tight_ci'])}",
            f"- button-sized boxes judged: {s['button_sized']}",
            f"- verdict: **{scoring.judged_verdict(s)}**",
            "",
        ]
    lines.append("Pass bar (written before judging): at least 30 judged answers and 8 button-sized boxes per model; "
                 "GO needs 85% on the right control and 60% tight; 70-85% is MITIGATE; below 70% is RETHINK.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", default=None)
    args = parser.parse_args()
    run_dir = os.path.abspath(args.run) if args.run else review.latest_run()
    if not os.path.exists(os.path.join(run_dir, "review", "judgments.json")):
        sys.exit("No judgments.json yet: judge the items in review/index.html and export it into the review folder.")
    text = report(run_dir)
    print(text)
    with open(os.path.join(run_dir, "review", "summary.md"), "w", encoding="utf-8") as f:
        f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
