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

## 2. Label them (about 15-20 minutes with suggestions)

First let the model write candidate questions for each screenshot (you still draw every box):

```bash
cd evals/pointing
python suggest.py --dataset data      # writes data/suggestions.json (6 questions per screenshot)
```

Then open `label.html` in your browser (double-click it; nothing to install):

1. **Choose screenshots**: select all the images in `data/`.
2. **Load suggestions.json** from the same folder.
3. For each screenshot, **click a suggested question**, then **drag a tight box** around the one control that
   answers it, and press Enter.
   - Don't like the wording? Edit the text before adding it, or type your own question instead.
   - Control not on screen, or the question is unclear? Press the cross to dismiss it.
4. Aim for **60 targets** in total (the counter at the top shows progress), including some small controls
   and a few questions you write yourself. Progress is saved in the browser as you go.
5. Click **Export labels.json** and save it into `data/`.

Every label records where its wording came from (`suggested`, `edited` or `manual`), and the report shows the
click-hit rate for each group, so we can see if AI-written questions are easier than yours.

Make the browser window as big as you can (maximise it): the whole screenshot is always fitted into the window,
so a bigger window means bigger screenshots and easier, more precise boxes.

Tips: label what you would *click*, not the whole row or panel. A good question describes the goal the way a
confused user would ("how do I make it stop sending me alerts?"), not the way the button is named.

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

## 4. If the labelled boxes turn out too coarse: judge the model's boxes by eye

The scored run needs *tight* boxes around single controls. If the labels are regions instead (the report says
"LABELS TOO COARSE" and shows the random-click baseline), the click-hit score only proves the model finds the
right *area*. A cheaper way to learn whether it finds the right *control* is for a person to look at each box the
model drew:

```bash
python review.py                # builds results/<run>/review/index.html (latest run)
```

Open that page in a browser. For each item you see the screenshot with the model's box in red, a zoomed view of
what is inside the box, and the question. Press **1** (right control, tight box), **2** (right control, but the box
is too big or loose), **3** (wrong control), **S** if you cannot tell, **B** to go back. The page is blind (it never
says which model drew the box) and shuffled, so you cannot favour either model. Click **Export judgments.json** and
save it into the `review` folder, then:

```bash
python review_report.py         # prints the verdict; only aggregates, no questions or file names
```

**The pass bar, written before any judging**, per model: at least 30 judged answers, of which at least 8 are
button-sized boxes (under 0.25% of the screen). **GO** needs 85% on the right control *and* 60% right-and-tight;
70-85% is **MITIGATE**; below 70% is **RETHINK**. A model that gave no usable answer counts as wrong, not as
missing. The report shows a 95% confidence range next to each rate, because with about 30 answers a measured 85%
could really be anywhere from roughly 70% to 94%.

Limits worth stating honestly: the judge is the person who chose the questions, and the question wording was
AI-suggested, so this is a human-judged eval, not a ground-truth one.

## What gets published

Only aggregate results (the summary table) and, if you choose, a few redacted overlays. Never the raw
screenshots.

## Tests

```bash
cd evals/pointing && pytest -q
```

Cover the parsing of model replies, the geometry, and the decision rule, including that a small sample can
never produce a verdict.
