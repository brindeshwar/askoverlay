import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import review  # noqa: E402
import review_report  # noqa: E402

SAMPLE = os.path.join(os.path.dirname(__file__), "sample")
IMAGE = "ui_real.png"   # the synthetic 1600x900 sample window


def record(model, question, pred, i=0):
    return {"model": model, "file": IMAGE, "question": question, "truth": [0, 0, 10, 10], "pred": pred,
            "seconds": 1.0, "error": None if pred else "RateLimit", "source": "suggested", "hit": False,
            "iou": 0.0, "iou_ok": False, "bucket": "large", "parsed": bool(pred), "area_frac": 0.3}


@pytest.fixture
def run_dir(tmp_path):
    button = [100, 100, 180, 130]          # button-sized: 80x30 on a 1600x900 screenshot = 0.17%
    panel = [100, 100, 900, 600]           # a big region
    records = [
        record("model-alpha", "How do I save?", button),
        record("model-beta", "How do I save?", panel),
        record("model-alpha", "Where is privacy? </script><b>x</b>", button),
        record("model-beta", "Where is privacy?", None),          # a failed answer
    ]
    (tmp_path / "results.json").write_text(json.dumps(records), encoding="utf-8")
    return str(tmp_path)


def test_the_review_page_is_blind(run_dir):
    review_dir = review.build(run_dir, SAMPLE, seed=1)
    page = open(os.path.join(review_dir, "index.html"), encoding="utf-8").read()
    assert "model-alpha" not in page and "model-beta" not in page
    assert "gemini" not in page.lower()
    for name in os.listdir(os.path.join(review_dir, "img")):
        assert "model" not in name and "alpha" not in name       # file names reveal nothing either
    key = json.load(open(os.path.join(review_dir, "key.json"), encoding="utf-8"))
    assert {v["model"] for v in key.values()} == {"model-alpha", "model-beta"}   # but the answer key has it


def test_failed_answers_are_not_shown_but_everything_else_is(run_dir):
    review_dir = review.build(run_dir, SAMPLE, seed=1)
    key = json.load(open(os.path.join(review_dir, "key.json"), encoding="utf-8"))
    assert len(key) == 3                                         # the failed one has no box to judge
    for item_id in key:
        assert os.path.exists(os.path.join(review_dir, "img", f"{item_id}.jpg"))
        assert os.path.exists(os.path.join(review_dir, "img", f"{item_id}_crop.jpg"))


def test_a_question_cannot_break_out_of_the_script_tag(run_dir):
    page = open(os.path.join(review.build(run_dir, SAMPLE, seed=1), "index.html"), encoding="utf-8").read()
    assert page.count("</script>") == 1                          # only the page's own closing tag


def test_order_is_shuffled_but_reproducible(run_dir):
    def order(seed):
        key = json.load(open(os.path.join(review.build(run_dir, SAMPLE, seed), "key.json"), encoding="utf-8"))
        return [key[k]["record"] for k in sorted(key)]

    assert order(1) == order(1)
    assert any(order(seed) != order(1) for seed in range(2, 12))


def test_button_sized_boxes_are_flagged_for_the_pass_bar(run_dir):
    key = json.load(open(os.path.join(review.build(run_dir, SAMPLE, seed=1), "key.json"), encoding="utf-8"))
    flags = sorted((v["model"], v["button_sized"]) for v in key.values())
    assert flags == [("model-alpha", True), ("model-alpha", True), ("model-beta", False)]


def test_report_counts_failures_as_wrong_and_unjudged_items_as_excluded(run_dir):
    review_dir = review.build(run_dir, SAMPLE, seed=1)
    key = json.load(open(os.path.join(review_dir, "key.json"), encoding="utf-8"))
    by_model = {}
    for item_id, info in key.items():
        by_model.setdefault(info["model"], []).append(item_id)
    judgments = {by_model["model-alpha"][0]: 1, by_model["model-alpha"][1]: 3, by_model["model-beta"][0]: "skip"}
    json.dump({"judgments": judgments}, open(os.path.join(review_dir, "judgments.json"), "w", encoding="utf-8"))

    text = review_report.report(run_dir)
    assert "## model-alpha" in text and "## model-beta" in text
    alpha = text.split("## model-alpha")[1].split("## model-beta")[0]
    beta = text.split("## model-beta")[1]
    assert "on the right control: **50%**" in alpha              # one right, one wrong
    assert "including 1 with no usable answer" in beta            # the failed answer is counted, as wrong
    assert "on the right control: **0%**" in beta                 # the failure is the only counted item; the skip is excluded
    assert "INSUFFICIENT DATA" in alpha                           # two answers can never be a verdict


def test_the_report_never_prints_questions_or_file_names(run_dir):
    review_dir = review.build(run_dir, SAMPLE, seed=1)
    json.dump({"judgments": {}}, open(os.path.join(review_dir, "judgments.json"), "w", encoding="utf-8"))
    text = review_report.report(run_dir)
    assert "How do I save" not in text and IMAGE not in text


# --- the self-contained page --------------------------------------------------------------------------------

def test_standalone_page_embeds_every_image_and_needs_no_folder(run_dir):
    import base64
    import io
    import re

    from PIL import Image

    review_dir = review.build(run_dir, SAMPLE, seed=1)
    page = open(os.path.join(review_dir, "standalone.html"), encoding="utf-8").read()
    assert 'img/i0' not in page                                  # no reference to the img folder at all
    uris = re.findall(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)", page)
    assert len(uris) == 6                                        # 3 shown items x (screenshot + zoom)
    for payload in uris:                                         # and each one is a real, decodable JPEG
        with Image.open(io.BytesIO(base64.b64decode(payload))) as image:
            assert image.format == "JPEG" and image.width > 10


def test_standalone_page_is_just_as_blind_and_script_safe(run_dir):
    page = open(os.path.join(review.build(run_dir, SAMPLE, seed=1), "standalone.html"), encoding="utf-8").read()
    assert "model-alpha" not in page and "model-beta" not in page and "gemini" not in page.lower()
    assert page.count("</script>") == 1


def test_both_pages_list_the_same_items_in_the_same_order(run_dir):
    review_dir = review.build(run_dir, SAMPLE, seed=1)

    def ids(name):
        page = open(os.path.join(review_dir, name), encoding="utf-8").read()
        import re
        return re.findall(r'"id": "(i\d+)"', page)

    assert ids("index.html") == ids("standalone.html") != []
