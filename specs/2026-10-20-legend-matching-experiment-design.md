# A legend-matching experiment for the colour separation floors

Date: 2026-10-20
Status: design, no code

From the academic review on `review-invariances`, item 7 of its list. Nothing
here is implemented, and nothing in the package changes until the experiment
has run.

## The gap

`check_palette.CVD_TARGET = 10.5` and `NORMAL_FLOOR = 21.0` are CAM02-UCS
distances set at 2x and 4x Stone et al.'s ND(50), the difference half of
observers detect at a given size. Detection is not the task a series colour
asks of a reader. A reader matches a stroke to a legend swatch, or tells two
series apart where they cross. No threshold in this package has human-subject
data for that task.

The literature review behind the CAM02-UCS decision found none either. Its
conclusion (`~/reports/Colour separation metric options.md`, "Conclusion"):
"No experiment maps any ND multiple, or any size and colour-difference
combination, onto legend matching or category identification", and "the
highest-value next step is not choosing a metric but the missing experiment:
legend-matching accuracy for pairs straddling 2x and 4x ND(50) at 0.2 to 0.35
deg". This document designs that experiment.

## The question

For two series in a line chart drawn at the sizes a printed figure uses, how
does legend-matching accuracy depend on their colour difference, in multiples
of ND(50) for that size?

Two answers would move a constant:

1. Accuracy at 4x ND(50) is not near ceiling. `NORMAL_FLOOR` is then too low
   for identification, whatever detection says.
2. Accuracy at 2x ND(50) already reaches the criterion below.
   `NORMAL_FLOOR` is then stricter than identification needs, and the floor
   becomes a convention to document rather than a requirement to defend.

## Stimuli

Each trial shows one line chart and its legend, rendered by matplotlib under
`skill/assets/figure.mplstyle`, so the stimuli are figures this package would
audit.

- **Series.** Four lines over 12 x positions, two of them the pair under test
  and two fillers whose colour clears both floors against everything else
  on the panel. The test pair crosses once. A crossing is where
  `_gated_pairs`' contact test compares a pair, and where a reader most needs
  to tell them apart.
- **Mark size.** Stroke width and legend swatch scaled so the stroke subtends
  0.20, 0.27 or 0.35 degrees at the viewing distance. 0.20 to 0.35 is the
  range the review names; 0.333 deg is Stone's per-axis column.
- **Colour difference.** Pairs drawn at 1x, 2x, 3x, 4x and 6x ND(50) for the
  mark size, in Stone's per-axis model, at fixed L*, a* and b* direction mixes.
  Each level is also given its CAM02-UCS distance, so the result can be read
  against the shipped constants directly.
- **Named pairs.** Added at their natural distance: sky blue against blue
  (`#56B4E9`/`#0072B2`), orange against vermilion (`#E69F00`/`#D55E00`), and
  the two shipped-cycle pairs Stone's model fails at 2x ND(50) under
  simulation (`#009E73`/`#CC79A7`, `#0072B2`/`#CC79A7`). Their measured
  distances are in `style-guide.md` and in
  `test_the_size_model_at_2x_fails_two_shipped_pairs_under_simulation`.
- **No second channel.** Every series is solid and markerless, so hue carries
  identity alone. That is the condition `CVD_TARGET`'s comment says needs a
  second channel below it, and the one `NORMAL_FLOOR` is not excused from.

## Task

A legend entry is highlighted, and the participant clicks the line it names.
The two test-pair entries and the two filler entries are each asked once per
chart, in random order. The measures are accuracy and response time. A
"cannot tell" button is offered, so a guess is not forced, and it is scored as
an error.

## Participants and viewing

- **Normal colour vision**, screened with a plate test administered in the
  session. Results are reported separately for anyone who fails it.
- **Red-green deficient observers**, recruited separately and screened the
  same way. Simulation is not a substitute: `check_palette`'s Machado and
  Viénot matrices are models of these observers, and what is being tested is
  whether the floors computed on those models predict their accuracy.
- **Viewing distance** is what turns stroke width into visual angle. In the
  laboratory it is fixed with a chin rest. Online, it is estimated per
  participant and each stimulus is scaled to it. Online estimation methods
  exist; which one to use is not settled here, and none is cited until it has
  been read.
- **Display.** Laboratory: a calibrated sRGB monitor at a recorded luminance.
  Online: uncalibrated, and so the online arm measures robustness rather than
  the threshold.

## Design and sample size

Within-subjects. 3 sizes x 5 ND levels x 3 direction mixes, plus the four
named pairs at each size, is 57 conditions. Each is shown 8 times with a
different random chart, which is 456 trials, about 30 minutes at 4 seconds a
trial.

Sample size is set so the comparison that decides the question has power. To
tell 95% accuracy from 90% at alpha 0.05 and power 0.8, the two-proportion
normal approximation needs about 434 trials per condition, before allowing for
trials clustering within participants. At 8 trials per participant per
condition that is about 55 participants per vision group before the design
effect, which a pilot has to estimate. The independent replication the review
cites (Hye, McNutt & Isaacs, 2026) ran N = 144 on a related detection task.
That is the scale to plan for until a pilot says otherwise.

## Analysis

Pre-registered before data collection:

- Mixed-effects logistic regression of accuracy on log ND multiple, size, and
  their interaction, with random intercepts for participant and for pair, and
  a random slope of ND multiple by participant.
- The identification threshold at each size: the ND multiple at which fitted
  accuracy reaches the criterion. **Criterion: 95%**, chosen in advance so
  the result cannot pick it.
- The same fit on CAM02-UCS distance instead of ND multiple, reported beside
  it, since the shipped constants are written in CAM02-UCS. Whichever metric
  predicts accuracy with less residual pair variance is the finding on the
  metric question that `qoo` left open.
- Named pairs reported individually with confidence intervals, whatever the
  model says.

## What each outcome does to the package

| Result | Change |
|---|---|
| Threshold at all sizes between 2x and 4x ND(50) | Constants stand. The docs cite the experiment as the identification basis, not detection plus a multiplier. |
| Threshold above 4x at the smallest size | `NORMAL_FLOOR` rises, or becomes size-dependent, which needs the mark's size on the page. `check_line_weight` already measures it. |
| Threshold below 2x everywhere | `NORMAL_FLOOR` is documented as conservative, and kept or lowered as a separate decision with its own corpus sweep. |
| Deficient observers' threshold not predicted by simulated distance | The CVD row's model is the defect, not the constant, and the simulation choice reopens. |

Any change to a constant goes through the repository's usual route: a test
written first against the new value, `make sweep` on the corpus, and the
measurement recorded in the changelog's "Why it changed".

## Not settled here

- Which online viewing-distance method to use, and the citation for it.
- Ethics review, which depends on where the experiment is run.
- Whether three direction mixes are enough to separate the L* axis from the
  chromatic ones. Stone's per-axis disagreement with CAM02-UCS is lightness-led
  (the review, "The disputed pairs are lightness-led"), so the L* mix may need
  more levels than the other two.
