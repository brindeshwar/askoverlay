"""Suggest "how do I...?" questions for each screenshot, to speed up labelling (you still draw every box).

    python suggest.py --dataset data

Writes <dataset>/suggestions.json, which label.html loads. The questions come from a model, so they lean a
little easier than a real user's; the labeller records whether each label was suggested, edited or typed by
hand so the result can be reported honestly. A different (larger) model than the ones being evaluated is
used by default, to avoid grading a model on questions it wrote for itself.
"""
import argparse
import asyncio
import json
import os
import re
import sys

import run_eval

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.1-flash-lite"
MAX_QUESTION_CHARS = 160

PROMPT = (
    "You are helping build a test set. This is a screenshot of a desktop application or website.\n"
    "Write {n} different questions that a confused, non-technical person might ask about how to do something on "
    "THIS screen. Each question must be answerable by clicking or using exactly ONE control that is clearly "
    "visible in the screenshot. Describe the goal, not the control's label (say \"how do I stop the alerts?\", not "
    "\"where is the Notifications toggle?\"). Include a mix of large and small controls (icons, checkboxes, tabs, "
    "menu items). Do not ask about anything that is not visible.\n"
    "Reply with ONLY a JSON array of {n} strings."
)

_ARRAY = re.compile(r"\[.*\]", re.DOTALL)
_BULLET = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")


def parse_questions(text: str, limit: int) -> list[str]:
    """Extract clean, unique questions from a model reply (JSON array preferred, bullet list as a fallback)."""
    candidates: list = []
    match = _ARRAY.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                candidates = parsed
        except json.JSONDecodeError:
            candidates = []
    if not candidates:
        candidates = [_BULLET.sub("", line) for line in text.splitlines() if "?" in line]

    seen, questions = set(), []
    for item in candidates:
        if not isinstance(item, str):
            continue
        question = " ".join(item.strip().strip('"').split())
        if not question or len(question) > MAX_QUESTION_CHARS or question.lower() in seen:
            continue
        seen.add(question.lower())
        questions.append(question)
        if len(questions) == limit:
            break
    return questions


async def suggest_for(llm_cls, key, models, b64, mime, count, timeout) -> list[str]:
    from langchain_core.messages import HumanMessage

    last_error = None
    for model in models:
        try:
            llm = llm_cls(model=model, api_key=key, temperature=0.7, max_retries=1, timeout=timeout)
            reply = await llm.ainvoke([HumanMessage(content=[
                {"type": "text", "text": PROMPT.format(n=count)},
                {"type": "image", "base64": b64, "mime_type": mime},
            ])])
            questions = parse_questions(run_eval.reply_text(reply), count)
            if questions:
                return questions
            last_error = "no usable questions in the reply"
        except Exception as exc:
            last_error = f"{type(exc).__name__}"
    raise RuntimeError(last_error or "unknown failure")


async def run(args) -> int:
    key = run_eval.load_key()
    from langchain_google_genai import ChatGoogleGenerativeAI

    dataset = os.path.abspath(args.dataset)
    out_path = os.path.join(dataset, "suggestions.json")
    existing = {}
    if os.path.exists(out_path) and not args.force:
        with open(out_path, encoding="utf-8") as f:
            existing = json.load(f)

    files = sorted(f for f in os.listdir(dataset) if f.lower().endswith(IMAGE_SUFFIXES))
    if not files:
        sys.exit(f"No screenshots found in {dataset}")
    result = dict(existing)
    failed = []
    models = [args.model, FALLBACK_MODEL]

    for index, name in enumerate(files, 1):
        if name in existing:
            continue
        b64, mime, _size = run_eval.prepare_image(os.path.join(dataset, name), args.max_edge, "jpeg")
        try:
            result[name] = await suggest_for(ChatGoogleGenerativeAI, key, models, b64, mime, args.per_image, args.timeout)
            print(f"  {index}/{len(files)}: {len(result[name])} suggestions", flush=True)
        except Exception as exc:  # one bad screenshot should not lose the rest
            failed.append(name)
            print(f"  {index}/{len(files)}: FAILED ({exc})", flush=True)
        with open(out_path, "w", encoding="utf-8") as f:  # save as we go so an interruption loses nothing
            json.dump(result, f, indent=1)
        await asyncio.sleep(0.3)

    total = sum(len(v) for v in result.values())
    print(f"\n{total} suggestions for {len(result)} of {len(files)} screenshots -> {out_path}")
    if failed:
        print(f"{len(failed)} screenshot(s) failed; run the command again to retry only those.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default="data", help="folder with the screenshots")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model that writes the questions")
    parser.add_argument("--per-image", type=int, default=6)
    parser.add_argument("--max-edge", type=int, default=1280)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--force", action="store_true", help="regenerate even for screenshots that already have suggestions")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
