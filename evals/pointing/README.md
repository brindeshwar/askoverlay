# Pointing eval

**Question this answers:** when a user asks "how do I do X?" about their screen, can the model return a box
around the right control, reliably enough to build the product on?

The product idea ("show me where to click": the overlay highlights the control) only works if the answer is
yes on *real* screens, not on a clean demo window. This eval measures it, and the decision rule below was
written **before** looking at any real results, so the numbers can't be talked into saying what we hope.

## The decision rule

Computed over at least **30 labelled targets** (below that the tool refuses to give a verdict):

| Outcome | Condition | What we do |
|---|---|---|
| **GO** | click lands on the target in at least 85% of questions, at least 70% on small targets, and box overlap (IoU >= 0.5) in at least 60% | Build the product on vision pointing |
| **MITIGATE** | click lands on the target in 70-85% | Add a refinement step first (below) |
| **RETHINK** | under 70% | Vision alone is not enough; rescope |

"Click lands on target" means the centre of the predicted box is inside the box you labelled. That is what
matters to a user. IoU is reported too, because a highlight that is drawn way too big looks wrong even if the
click would land.

If the result is MITIGATE, the options are: a second pass that crops and zooms the region the model chose and
asks again; or, for native Windows apps, snapping the model's box to the nearest control reported by the
Windows UI Automation tree, which has exact rectangles.

## 1. Collect screenshots (about 20)

- Use the apps you actually use: code editor, browser (a few different websites), Windows Settings, a PDF
  reader, a spreadsheet, a chat app, and so on. Aim for at least 6 different apps.
- Include hard cases on purpose: dense toolbars, icon-only buttons, small checkboxes, dark and light themes,
  a crowded web page. An eval made only of easy screens proves nothing.
- Take them at your normal screen resolution (Win+Shift+S, or Print Screen).
- **Privacy:** screenshots may contain personal information. Crop or avoid anything sensitive. They are
  sent to Google's API when you run the eval. Put them in `evals/pointing/data/`, which is git-ignored.

## 2. Label them (about 30-40 minutes)

Open `label.html` in your browser (double-click it; nothing to install).

1. Choose all the screenshots.
2. For each one, drag a tight box around a control, type the question a user would ask ("How do I turn on
   dark mode?"), press Enter. Aim for 3-4 targets per screenshot, at least 60 in total, including some
   small ones.
3. Progress is saved in the browser as you go. Click **Export labels.json** when done and save it next to the
   screenshots, as `data/labels.json`.

Tips: label what you would *click*, not the whole row or panel. Ask the way a confused user would, not the way
the button is named ("how do I make it stop sending me alerts?" rather than "Notifications toggle").

## 3. Run

```bash
cd evals
pip install -r requirements.txt          # or use the backend virtualenv
cd pointing
python run_eval.py --dataset data
```

The key is read from `GEMINI_API_KEY`, or from `BACKEND_GEMINI_KEY` in `backend/.env`. Options:
`--models`, `--max-edge 1280` (the size the product will send; `0` = full size), `--format jpeg|png`,
`--overlays misses|all|none`.

Results go to `results/<timestamp>/`: `summary.md`, `results.json`, and `overlays/` with a picture for every
miss (green = where it should be, red = where the model pointed). **Look at the overlays**: they tell you
*why* it fails, which numbers alone don't.

`python run_eval.py` with no arguments runs on `sample/` (one synthetic window, 8 targets), which exists to
check that the tool works; it will correctly report INSUFFICIENT DATA.

## What gets published

Only aggregate results (the summary table) and, if you choose, a few redacted overlays. Never the raw
screenshots.

## Tests

```bash
cd evals/pointing && pytest -q
```

Cover the parsing of model replies, the geometry, and the decision rule, including that a small sample can
never produce a verdict.
