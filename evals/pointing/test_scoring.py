import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import scoring  # noqa: E402


# --- parsing the model's reply -----------------------------------------------------------------------

@pytest.mark.parametrize(
    "reply, expected",
    [
        ('{"box_2d": [100, 200, 300, 400]}', [100, 200, 300, 400]),
        ('```json\n{"box_2d": [10.5, 20, 30.25, 40]}\n```', [10.5, 20, 30.25, 40]),
        ("Sure! The box is [0, 0, 1000, 1000].", [0, 0, 1000, 1000]),
    ],
)
def test_parse_accepts_the_formats_models_actually_return(reply, expected):
    assert scoring.parse_box_norm(reply) == expected


@pytest.mark.parametrize(
    "reply",
    [
        "I can't find that control.",
        '{"box_2d": []}',
        "[300, 100, 100, 400]",    # ymin > ymax
        "[100, 400, 300, 200]",    # xmin > xmax
        "[100, 100, 100, 200]",    # zero height
        "[100, 200, 1200, 400]",   # outside the 0-1000 range
        "[-5, 200, 300, 400]",
    ],
)
def test_parse_rejects_unusable_boxes_instead_of_guessing(reply):
    assert scoring.parse_box_norm(reply) is None


def test_norm_to_pixels_maps_axes_correctly():
    # [ymin, xmin, ymax, xmax] on a 2000x1000 image -> [x1, y1, x2, y2]
    assert scoring.norm_to_pixels([100, 200, 300, 400], width=2000, height=1000) == [400, 100, 800, 300]


# --- geometry ---------------------------------------------------------------------------------------

def test_iou_identical_disjoint_and_half_overlap():
    box = [0, 0, 10, 10]
    assert scoring.iou(box, box) == 1.0
    assert scoring.iou(box, [20, 20, 30, 30]) == 0.0
    assert scoring.iou(box, [5, 0, 15, 10]) == pytest.approx(1 / 3)  # 50 overlap / 150 union


def test_iou_of_degenerate_boxes_is_zero_not_a_crash():
    assert scoring.iou([0, 0, 0, 0], [0, 0, 0, 0]) == 0.0


def test_center_hit_uses_the_centre_of_the_prediction():
    truth = [100, 100, 200, 140]
    assert scoring.center_hit([90, 95, 210, 145], truth)       # slightly loose box, centre inside
    assert not scoring.center_hit([150, 100, 400, 140], truth)  # centre at x=275, outside
    assert scoring.center_hit([100, 100, 200, 140], truth)     # edges are inclusive


def test_a_huge_box_around_everything_is_not_rewarded_by_iou():
    truth = [100, 100, 200, 140]
    result = scoring.score([0, 0, 1000, 1000], truth, width=1000, height=1000)
    assert result["iou_ok"] is False  # 1% of the area is nowhere near 50% overlap


# --- score / buckets --------------------------------------------------------------------------------

def test_missing_prediction_counts_as_a_miss_not_an_exclusion():
    result = scoring.score(None, [0, 0, 10, 10], 100, 100)
    assert (result["parsed"], result["hit"], result["iou_ok"]) == (False, False, False)


def test_size_buckets_by_fraction_of_screenshot_area():
    w, h = 1000, 1000  # 1,000,000 px^2
    assert scoring.size_bucket([0, 0, 40, 40], w, h) == "small"      # 0.16%
    assert scoring.size_bucket([0, 0, 100, 100], w, h) == "medium"   # 1%
    assert scoring.size_bucket([0, 0, 500, 500], w, h) == "large"    # 25%


# --- aggregation and the decision rule -----------------------------------------------------------------

def rec(hit, iou_value, bucket="medium", parsed=True, area_frac=0.01):
    return {"parsed": parsed, "hit": hit, "iou": iou_value, "iou_ok": iou_value >= 0.5, "bucket": bucket, "area_frac": area_frac}


def test_summarize_computes_rates_overall_and_per_bucket():
    summary = scoring.summarize([rec(True, 0.9, "small"), rec(False, 0.0, "small"), rec(True, 0.8, "large")])
    assert summary["overall"]["n"] == 3
    assert summary["overall"]["hit"] == pytest.approx(2 / 3)
    assert summary["small"]["hit"] == 0.5
    assert summary["medium"]["n"] == 0 and summary["medium"]["hit"] is None


def test_verdict_thresholds_are_the_ones_written_in_the_readme():
    def verdict_of(records):
        return scoring.verdict(scoring.summarize(records), min_targets=4, min_small=0)

    good = [rec(True, 0.8, "small")] * 9 + [rec(False, 0.0, "small")]
    assert verdict_of([rec(True, 0.8)] * 20).startswith("GO")
    assert verdict_of(good).startswith("GO")  # 90% hit, small targets 90%
    assert verdict_of([rec(True, 0.8)] * 3 + [rec(False, 0.0)]).startswith("MITIGATE")  # 75% hit
    assert verdict_of([rec(True, 0.8)] + [rec(False, 0.0)] * 3).startswith("RETHINK")  # 25% hit
    assert verdict_of([]) == "no data"


def test_a_small_sample_can_never_produce_a_verdict():
    perfect_but_tiny = scoring.summarize([rec(True, 0.9, "small")] * 8)
    assert scoring.verdict(perfect_but_tiny).startswith("INSUFFICIENT DATA")
    enough = scoring.summarize([rec(True, 0.9, "small")] * scoring.MIN_TARGETS)
    assert scoring.verdict(enough).startswith("GO")


def test_no_small_targets_means_no_verdict_instead_of_a_free_pass():
    """Regression: a dataset with no small targets used to skip the small-target requirement and could say GO."""
    only_big = scoring.summarize([rec(True, 0.9, "large")] * 40)
    assert scoring.verdict(only_big).startswith("INCOMPLETE")
    few_small = scoring.summarize([rec(True, 0.9, "small")] * 7 + [rec(True, 0.9, "large")] * 40)
    assert scoring.verdict(few_small).startswith("INCOMPLETE")


def test_labels_that_are_regions_not_controls_are_flagged_by_the_random_click_baseline():
    coarse = scoring.summarize([rec(True, 0.9, "large", area_frac=0.35)] * 40)
    assert coarse["random_click_baseline"] == pytest.approx(0.35)
    assert scoring.verdict(coarse).startswith("LABELS TOO COARSE")


def test_the_baseline_is_the_mean_share_of_the_screen_covered_by_the_boxes():
    summary = scoring.summarize([rec(True, 0.9, area_frac=0.01), rec(True, 0.9, area_frac=0.03)])
    assert summary["random_click_baseline"] == pytest.approx(0.02)
    assert scoring.summarize([])["random_click_baseline"] is None


def test_score_records_how_much_of_the_screen_the_target_covers():
    result = scoring.score([0, 0, 10, 10], [0, 0, 50, 20], width=100, height=100)
    assert result["area_frac"] == pytest.approx(0.10)


def test_labels_keep_the_source_of_the_wording_and_default_to_unknown():
    text = json.dumps({"images": [{"file": "a.png", "targets": [
        {"question": "q1", "box": [1, 2, 30, 40], "source": "edited"},
        {"question": "q2", "box": [5, 5, 9, 9]}]}]})
    assert [t["source"] for t in scoring.labels_from_json(text)] == ["edited", "unknown"]


def test_source_breakdown_shows_whether_suggested_questions_are_easier():
    records = (
        [dict(rec(True, 0.9), source="suggested")] * 3
        + [dict(rec(False, 0.0), source="manual")] * 2
        + [dict(rec(True, 0.9), source="manual")]
    )
    breakdown = scoring.source_breakdown(records)
    assert breakdown["suggested"] == {"n": 3, "hit": 1.0}
    assert breakdown["manual"]["n"] == 3 and abs(breakdown["manual"]["hit"] - 1 / 3) < 1e-9


def test_a_strong_overall_score_cannot_hide_failure_on_small_targets():
    records = [rec(True, 0.9, "large")] * 18 + [rec(False, 0.0, "small")] * 2 + [rec(True, 0.9, "small")] * 0
    summary = scoring.summarize(records)
    assert summary["overall"]["hit"] == 0.9
    assert not scoring.verdict(summary, min_targets=10).startswith("GO")  # small targets: 0% hit


# --- labels file ------------------------------------------------------------------------------------

def test_labels_are_flattened_and_validated():
    text = json.dumps({"images": [{"file": "a.png", "targets": [
        {"question": " How do I save? ", "box": [1, 2, 30, 40]},
        {"question": "Where is search?", "box": [5, 5, 9, 9]}]}]})
    flat = scoring.labels_from_json(text)
    assert [t["question"] for t in flat] == ["How do I save?", "Where is search?"]
    assert flat[0]["file"] == "a.png"


@pytest.mark.parametrize(
    "target",
    [
        {"question": "q", "box": [10, 10, 5, 20]},
        {"question": "q", "box": [1, 2, 3]},
        {"question": "   ", "box": [1, 2, 30, 40]},
        {"question": "q"},
    ],
)
def test_bad_labels_fail_loudly(target):
    with pytest.raises(ValueError):
        scoring.labels_from_json(json.dumps({"images": [{"file": "a.png", "targets": [target]}]}))
