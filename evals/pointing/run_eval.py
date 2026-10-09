"""Run the pointing eval: for every labelled question, ask the model where to click and score the answer.

    python run_eval.py --dataset sample
    python run_eval.py --dataset data --models gemini-3.5-flash-lite gemini-3.1-flash-lite

The dataset folder holds the screenshots and a labels.json (made with label.html). Uses the same chat-model
class as the product. The key comes from GEMINI_API_KEY, or else from the backend's BACKEND_GEMINI_KEY setting;
it is never printed or written to the results.
"""
import argparse
import asyncio
import base64
import io
import json
import os
import re
import sys
import time
import warnings
from datetime import datetime

from PIL import Image, ImageDraw

import scoring

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.normpath(os.path.join(HERE, "..", "..", "backend"))

DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]

# Candidate production prompt: if the eval validates it, it moves into the backend unchanged.
PROMPT = (
    "This is a screenshot of a desktop application or website. {question}\n"
    "Reply with ONLY a JSON object {{\"box_2d\": [ymin, xmin, ymax, xmax]}} giving the bounding box of the single "
    "UI element the user should click or use, with coordinates normalized to 0-1000."
)


def load_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    sys.path.insert(0, BACKEND)
    previous = os.getcwd()
    os.chdir(BACKEND)  # the backend's settings look for .env in the working directory
    try:
        from config import get_settings

        key = get_settings().backend_gemini_key
    finally:
        os.chdir(previous)
    if not key:
        sys.exit("No key: set GEMINI_API_KEY or BACKEND_GEMINI_KEY in backend/.env")
    return key


def prepare_image(path: str, max_edge: int, fmt: str) -> tuple[str, str, tuple[int, int]]:
    """Return (base64, mime, original size). The image is downscaled the way the product will, then encoded."""
    image = Image.open(path).convert("RGB")
    original_size = image.size
    if max_edge and max(image.size) > max_edge:
        scale = max_edge / max(image.size)
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    buffer = io.BytesIO()
    if fmt == "jpeg":
        image.save(buffer, format="JPEG", quality=85)
        mime = "image/jpeg"
    else:
        image.save(buffer, format="PNG")
        mime = "image/png"
    return base64.b64encode(buffer.getvalue()).decode(), mime, original_size


def reply_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") != "thinking")


def draw_overlay(path: str, truth, pred, out_path: str) -> None:
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle(truth, outline=(0, 200, 0), width=4)          # green: where it should be
    if pred:
        draw.rectangle(pred, outline=(230, 0, 0), width=4)       # red: where the model pointed
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    image.save(out_path)


async def ask(llm_cls, key, model, b64, mime, question, timeout):
    from langchain_core.messages import HumanMessage

    llm = llm_cls(model=model, api_key=key, temperature=0, max_retries=1, timeout=timeout)
    started = time.time()
    reply = await llm.ainvoke([HumanMessage(content=[
        {"type": "text", "text": PROMPT.format(question=question)},
        {"type": "image", "base64": b64, "mime_type": mime},
    ])])
    return reply_text(reply), time.time() - started


async def run(args) -> int:
    key = load_key()
    from langchain_google_genai import ChatGoogleGenerativeAI

    dataset = os.path.abspath(args.dataset)
    with open(os.path.join(dataset, "labels.json"), encoding="utf-8") as f:
        labels = scoring.labels_from_json(f.read())
    if not labels:
        sys.exit("labels.json has no targets")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(HERE, "results", run_id)
    os.makedirs(out_dir, exist_ok=True)
    cache = {}
    records = []
    print(f"{len(labels)} targets, models: {', '.join(args.models)}, max_edge={args.max_edge or 'none'}, format={args.format}\n")

    for index, label in enumerate(labels):
        path = os.path.join(dataset, label["file"])
        if path not in cache:
            cache[path] = prepare_image(path, args.max_edge, args.format)
        b64, mime, (width, height) = cache[path]
        for model in args.models:
            error = None
            pred_px = None
            seconds = 0.0
            try:
                text, seconds = await ask(ChatGoogleGenerativeAI, key, model, b64, mime, label["question"], args.timeout)
                norm = scoring.parse_box_norm(text)
                pred_px = scoring.norm_to_pixels(norm, width, height) if norm else None
            except Exception as exc:  # a failed call is a miss, and is reported as such
                error = re.sub(re.escape(key), "***", f"{type(exc).__name__}: {str(exc)[:120]}")
            result = scoring.score(pred_px, label["box"], width, height)
            record = {"model": model, "file": label["file"], "question": label["question"], "truth": label["box"],
                      "pred": pred_px, "seconds": seconds, "error": error, **result}
            records.append(record)
            if args.overlays != "none" and (args.overlays == "all" or not result["hit"]):
                draw_overlay(path, label["box"], pred_px, os.path.join(out_dir, "overlays", f"{model}_{index:03d}.png"))
            await asyncio.sleep(args.delay)
        print(f"  {index + 1}/{len(labels)} {label['file']}: {label['question']}", flush=True)

    report = report_text(records, args.models)
    print("\n" + report)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=1)
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nSaved to {out_dir}")
    return 0


def pct(value) -> str:
    return "  n/a" if value is None else f"{value * 100:4.0f}%"


def report_text(records: list[dict], models: list[str]) -> str:
    lines = []
    for model in models:
        rows = [r for r in records if r["model"] == model]
        summary = scoring.summarize(rows)
        times = sorted(r["seconds"] for r in rows if not r["error"])
        median = times[len(times) // 2] if times else float("nan")
        lines.append(f"## {model}   ({len(rows)} targets, median {median:.1f}s, {sum(1 for r in rows if r['error'])} call errors)")
        lines.append("")
        lines.append("| size | n | click lands on target | box overlap >= 0.5 | mean IoU | parsed |")
        lines.append("|---|---|---|---|---|---|")
        for bucket in ("overall", "small", "medium", "large"):
            s = summary[bucket]
            mean_iou = "  n/a" if s["mean_iou"] is None else f"{s['mean_iou']:.2f}"
            lines.append(f"| {bucket} | {s['n']} | {pct(s['hit'])} | {pct(s['iou_ok'])} | {mean_iou} | {pct(s['parsed'])} |")
        lines.append("")
        lines.append(f"Verdict: **{scoring.verdict(summary)}**")
        misses = [r for r in rows if not r["hit"]]
        if misses:
            lines.append("")
            lines.append(f"Misses ({len(misses)}):")
            for r in misses[:15]:
                lines.append(f"- {r['file']}: \"{r['question']}\"" + (f"  [{r['error']}]" if r["error"] else ""))
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=os.path.join(HERE, "sample"), help="folder with screenshots and labels.json")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--max-edge", type=int, default=1280, help="downscale so the longest edge is this (0 = none)")
    parser.add_argument("--format", choices=["jpeg", "png"], default="jpeg", help="how the screenshot is encoded")
    parser.add_argument("--overlays", choices=["misses", "all", "none"], default="misses")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--delay", type=float, default=0.3, help="seconds between calls")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
