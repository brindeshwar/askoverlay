"""Build a blind review page from an eval run, so a person can judge whether each model box is on the right control.

    python review.py                 # latest run in results/
    python review.py --run results/20261012-023128

Writes <run>/review/standalone.html (images built in; works anywhere, including preview panes) and index.html (the
same page, smaller, loading images from the img/ folder next to it). Open one in a browser, press 1 / 2 / 3 for each
item, export judgments.json into the review folder, then run:  python review_report.py

Which model produced each box is hidden (it lives in review/key.json, which the page never loads) and the order is
shuffled, so a judge cannot favour a model. Everything stays local: results/ is git-ignored.
"""
import argparse
import base64
import glob
import io
import json
import os
import random
import sys

from PIL import Image, ImageDraw

import scoring

HERE = os.path.dirname(os.path.abspath(__file__))
RED = (230, 0, 0)
MAX_SHOT_EDGE = 1600
CROP_WIDTH = 560


def latest_run() -> str:
    runs = sorted(glob.glob(os.path.join(HERE, "results", "*", "results.json")))
    if not runs:
        sys.exit("No eval runs found in results/. Run run_eval.py first.")
    return os.path.dirname(runs[-1])


def draw_box(image: Image.Image, box, width: int) -> None:
    ImageDraw.Draw(image).rectangle(box, outline=RED, width=width)


def make_shot(source: Image.Image, box) -> Image.Image:
    """The whole screenshot with the model's box drawn on it (scaled down if huge)."""
    shot = source.copy()
    draw_box(shot, box, max(3, source.width // 400))
    if max(shot.size) > MAX_SHOT_EDGE:
        scale = MAX_SHOT_EDGE / max(shot.size)
        shot = shot.resize((round(shot.width * scale), round(shot.height * scale)), Image.LANCZOS)
    return shot


def make_crop(source: Image.Image, box) -> Image.Image:
    """A zoomed view around the box, so a button-sized box can be judged by eye."""
    x1, y1, x2, y2 = box
    margin = max(x2 - x1, y2 - y1, 80) * 1.5
    left, top = max(0, int(x1 - margin)), max(0, int(y1 - margin))
    right, bottom = min(source.width, int(x2 + margin)), min(source.height, int(y2 + margin))
    crop = source.crop((left, top, right, bottom))
    draw_box(crop, (x1 - left, y1 - top, x2 - left, y2 - top), 2)
    scale = min(CROP_WIDTH / crop.width, 6)
    return crop.resize((max(1, round(crop.width * scale)), max(1, round(crop.height * scale))), Image.LANCZOS)


def data_uri(path: str, max_edge: int, quality: int) -> str:
    """A JPEG file as a data: URI, re-encoded smaller so the self-contained page stays a reasonable size."""
    with Image.open(path) as image:
        image = image.convert("RGB")
        if max(image.size) > max_edge:
            scale = max_edge / max(image.size)
            image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def write_page(template: str, items: list[dict], path: str) -> None:
    data = json.dumps(items).replace("</", "<\\/")     # keep a question containing "</script>" from breaking the page
    with open(path, "w", encoding="utf-8") as f:
        f.write(template.replace("/*DATA*/[]", data))


def build(run_dir: str, dataset: str, seed: int) -> str:
    with open(os.path.join(run_dir, "results.json"), encoding="utf-8") as f:
        records = json.load(f)
    run_name = os.path.basename(run_dir)
    review_dir = os.path.join(run_dir, "review")
    os.makedirs(os.path.join(review_dir, "img"), exist_ok=True)

    candidates = [(i, r) for i, r in enumerate(records) if r["pred"]]   # failures are counted as wrong by the report
    random.Random(seed).shuffle(candidates)

    items, key = [], {}
    sources: dict[str, Image.Image] = {}
    for n, (record_index, r) in enumerate(candidates):
        if r["file"] not in sources:
            sources[r["file"]] = Image.open(os.path.join(dataset, r["file"])).convert("RGB")
        source = sources[r["file"]]
        item_id = f"i{n:03d}"
        box = [max(0, r["pred"][0]), max(0, r["pred"][1]), min(source.width, r["pred"][2]), min(source.height, r["pred"][3])]
        make_shot(source, box).save(os.path.join(review_dir, "img", f"{item_id}.jpg"), quality=85)
        make_crop(source, box).save(os.path.join(review_dir, "img", f"{item_id}_crop.jpg"), quality=88)
        area = (box[2] - box[0]) * (box[3] - box[1]) / (source.width * source.height)
        items.append({"id": item_id, "run": run_name, "shot": f"img/{item_id}.jpg", "crop": f"img/{item_id}_crop.jpg",
                      "question": r["question"]})
        key[item_id] = {"model": r["model"], "record": record_index, "button_sized": area < scoring.BUTTON_SIZED}

    with open(os.path.join(HERE, "review_template.html"), encoding="utf-8") as f:
        template = f.read()
    write_page(template, items, os.path.join(review_dir, "index.html"))
    # The same page with the images built in. It needs no folder next to it, so it also works in a preview pane and
    # when moved; index.html (smaller, loads images from img/) is for a normal browser.
    embedded = [
        dict(it, shot=data_uri(os.path.join(review_dir, it["shot"]), 1280, 78),
             crop=data_uri(os.path.join(review_dir, it["crop"]), 520, 80))
        for it in items
    ]
    write_page(template, embedded, os.path.join(review_dir, "standalone.html"))
    with open(os.path.join(review_dir, "key.json"), "w", encoding="utf-8") as f:   # never loaded by the page
        json.dump(key, f, indent=1)
    return review_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", default=None, help="a results/<run> folder (default: the latest)")
    parser.add_argument("--dataset", default=os.path.join(HERE, "data"))
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()
    run_dir = os.path.abspath(args.run) if args.run else latest_run()
    review_dir = build(run_dir, os.path.abspath(args.dataset), args.seed)
    size_mb = os.path.getsize(os.path.join(review_dir, "standalone.html")) / 1e6
    print(f"Review page ready: {os.path.join(review_dir, 'standalone.html')}  ({size_mb:.1f} MB, images built in)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
