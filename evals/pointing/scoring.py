"""Scoring for the pointing eval: parse the model's box, compare it with the labelled one.

Boxes are [x1, y1, x2, y2] in image pixels unless a name says "norm". The model is asked for Gemini's native
format, [ymin, xmin, ymax, xmax] normalised to 0-1000, which is independent of image size - so downscaling a
screenshot before sending it does not change how predictions map back to the original.
"""
import json
import re

_FOUR_NUMBERS = re.compile(r"\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]")

# Target size as a fraction of the screenshot's area. Small targets (icon buttons, checkboxes) are the hard ones.
SMALL_MAX = 0.0025
MEDIUM_MAX = 0.02


def parse_box_norm(text: str) -> list[float] | None:
    """Pull [ymin, xmin, ymax, xmax] (0-1000) out of a model reply; None if there is no usable box."""
    match = _FOUR_NUMBERS.search(text)
    if not match:
        return None
    ymin, xmin, ymax, xmax = (float(g) for g in match.groups())
    if not (0 <= ymin < ymax <= 1000 and 0 <= xmin < xmax <= 1000):
        return None
    return [ymin, xmin, ymax, xmax]


def norm_to_pixels(box_norm: list[float], width: int, height: int) -> list[float]:
    ymin, xmin, ymax, xmax = box_norm
    return [xmin * width / 1000, ymin * height / 1000, xmax * width / 1000, ymax * height / 1000]


def iou(a: list[float], b: list[float]) -> float:
    inter_w = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    inter_h = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = inter_w * inter_h
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def center_hit(pred: list[float], truth: list[float]) -> bool:
    """Would a click at the centre of the predicted box land on the labelled control?"""
    cx, cy = (pred[0] + pred[2]) / 2, (pred[1] + pred[3]) / 2
    return truth[0] <= cx <= truth[2] and truth[1] <= cy <= truth[3]


def size_bucket(truth: list[float], width: int, height: int) -> str:
    area = (truth[2] - truth[0]) * (truth[3] - truth[1]) / (width * height)
    if area < SMALL_MAX:
        return "small"
    return "medium" if area < MEDIUM_MAX else "large"


def score(pred_px: list[float] | None, truth: list[float], width: int, height: int) -> dict:
    """Score one prediction. A missing prediction is a miss, not an exclusion."""
    bucket = size_bucket(truth, width, height)
    area_frac = (truth[2] - truth[0]) * (truth[3] - truth[1]) / (width * height)
    if pred_px is None:
        return {"parsed": False, "hit": False, "iou": 0.0, "iou_ok": False, "bucket": bucket, "area_frac": area_frac}
    value = iou(pred_px, truth)
    return {"parsed": True, "hit": center_hit(pred_px, truth), "iou": value, "iou_ok": value >= 0.5,
            "bucket": bucket, "area_frac": area_frac}


def summarize(records: list[dict]) -> dict:
    """Aggregate per-target records (each has the keys from score()) into rates, overall and per size bucket."""

    def rates(rows: list[dict]) -> dict:
        n = len(rows)
        if n == 0:
            return {"n": 0, "parsed": None, "hit": None, "iou_ok": None, "mean_iou": None}
        return {
            "n": n,
            "parsed": sum(r["parsed"] for r in rows) / n,
            "hit": sum(r["hit"] for r in rows) / n,
            "iou_ok": sum(r["iou_ok"] for r in rows) / n,
            "mean_iou": sum(r["iou"] for r in rows) / n,
        }

    summary = {"overall": rates(records)}
    for bucket in ("small", "medium", "large"):
        summary[bucket] = rates([r for r in records if r["bucket"] == bucket])
    # Chance that a click at a uniformly random spot lands on the target: the average share of the screen the
    # labelled boxes cover. A score is only meaningful well above this.
    fractions = [r["area_frac"] for r in records if "area_frac" in r]
    summary["random_click_baseline"] = sum(fractions) / len(fractions) if fractions else None
    return summary


MIN_TARGETS = 30       # below this a percentage is an anecdote, not evidence
MIN_SMALL_TARGETS = 8  # buttons and icons are the hard, product-defining case; without them there is no verdict
MAX_BASELINE = 0.15    # if a random click would already hit this often, the boxes are regions, not controls


def source_breakdown(records: list[dict]) -> dict:
    """Click-hit rate by where the question wording came from, to show whether AI-written questions are easier."""
    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(r.get("source", "unknown"), []).append(r)
    return {name: {"n": len(rows), "hit": sum(r["hit"] for r in rows) / len(rows)} for name, rows in sorted(groups.items())}


def verdict(summary: dict, min_targets: int = MIN_TARGETS, min_small: int = MIN_SMALL_TARGETS) -> str:
    """The decision rule, written down BEFORE seeing real results (see README): go / mitigate / rethink."""
    overall = summary["overall"]
    if overall["n"] == 0:
        return "no data"
    if overall["n"] < min_targets:
        return f"INSUFFICIENT DATA: {overall['n']} targets, need at least {min_targets} before trusting any verdict"
    baseline = summary.get("random_click_baseline")
    if baseline is not None and baseline > MAX_BASELINE:
        return (f"LABELS TOO COARSE: a random click would already hit {baseline * 100:.0f}% of these targets, so the "
                "score cannot show whether the model can point at a button. Label tighter boxes around single controls")
    if summary["small"]["n"] < min_small:
        return (f"INCOMPLETE: only {summary['small']['n']} small targets, need at least {min_small}; "
                "the test cannot say whether pointing works for buttons and icons")
    small_hit = summary["small"]["hit"]
    # None only when min_small was explicitly set to 0 (tests); with the default there are always small targets here.
    small_ok = small_hit is None or small_hit >= 0.70
    if overall["hit"] >= 0.85 and small_ok and overall["iou_ok"] >= 0.60:
        return "GO: pointing is reliable enough to build the product on"
    if overall["hit"] >= 0.70:
        return "MITIGATE: workable, but add a refinement step (see README) before relying on it"
    return "RETHINK: vision alone is not reliable enough for pointing"


def labels_from_json(text: str) -> list[dict]:
    """Validate and flatten labels.json into [{file, question, box}], raising ValueError with a clear message."""
    data = json.loads(text)
    flat = []
    for image in data.get("images", []):
        for target in image.get("targets", []):
            box = target.get("box")
            if not (isinstance(box, list) and len(box) == 4 and box[0] < box[2] and box[1] < box[3]):
                raise ValueError(f"bad box for {image.get('file')}: {box!r}")
            if not str(target.get("question", "")).strip():
                raise ValueError(f"empty question for {image.get('file')}")
            flat.append({
                "file": image["file"],
                "question": target["question"].strip(),
                "box": [float(v) for v in box],
                "source": target.get("source", "unknown"),  # suggested / edited / manual, from the labeler
            })
    return flat
