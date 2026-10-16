# ADR-0008: Product direction "show me where" - GO by the pre-registered rule, with caveats

- Status: Accepted
- Date: 2026-10-12
- Related: Evidence base for the pointing capability. A different product direction is proposed in ADR-0009; the evidence stays valid either way.

**Context.** The product idea is "ask how to do X; the overlay highlights the control to click". It only works if
the model points at the right control on real screens. A first scored run was inconclusive (the labelled boxes
were regions, so a random click would already have scored 40%; the rule correctly refused a verdict). A second,
human-judged run fixed its pass bar before any judging: per model at least 30 judged answers and 8 button-sized
boxes; GO needs 85% on the right control and 60% right-and-tight; 70-85% is MITIGATE; below 70% is RETHINK.

**Evidence** (20 real screenshots from the owner's own apps, 60 questions, both models judged blind and shuffled
on 115 boxes by the owner; a model that gave no usable answer counts as wrong; ranges are 95% confidence):

| | right control | right and tight | no usable answer |
|---|---|---|---|
| `gemini-3.5-flash-lite` (primary) | 87% (76-93%) | 80% (68-88%) | 0 of 60 |
| `gemini-3.1-flash-lite` (fallback) | 85% (74-92%) | 73% (61-83%) | 5 of 60 |

Both pass the rule; 3.1 sits exactly on the 85% line (51 of 60), so "passes" is the honest word, not "comfortably".

**What the headline hides.** Larger targets were right 17 of 17 for each model, which lifts the average. On
**button-sized boxes only** (the product's real claim): 3.5 was right on 81% (67-90%) and tight on 72%; 3.1 right
on about 89% of the 38 it answered (76-96%), but about 79% once its 5 failures are counted. So, for small
controls, expect roughly 4 in 5 correct, not 9 in 10. The two models agree on where to point (boxes overlap) in
49 of 55 shared questions; where they agree the primary was right 44 of 49, where they disagree 4 of 6 (too few
to rely on). Both were wrong together on 4 questions, so a second model would rescue only 3 of 55.

**Limits of the evidence.** One judge, who also chose the questions; all 60 questions were AI-suggested; 20
screenshots from one person's apps; free-tier key, one day. This is a human-judged eval, not independent ground
truth, and says nothing about other users' screens, languages or themes.

**Decision.** Build the product on vision pointing, designed for being wrong about 1 time in 5 on small controls:
a short label beside the highlight, a one-click "not this one" that asks again excluding the rejected box, and local
feedback logging. Keep the fallback model for availability (0 of 60 failures for the primary vs 5 of 60), not as
an accuracy booster. Treat a refinement pass (crop and zoom, or snapping to Windows UI Automation rectangles) as a
later experiment. The 92 boxes the judge marked "right and tight" are now verified boxes, a cheap regression set
for future prompt or model changes (biased towards what these models already do).

**What may be claimed.** "Points at the right control about 85% of the time on 20 real screens (n=60, 95%
confidence 76-93%); about 80% for button-sized controls." Nothing stronger.
