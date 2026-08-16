# Design

How the two checkers make their decisions, what a passing run means, and the
design notes behind the thresholds. This page is the concept material; [the
gates](gates.md) is the reference for what each row measures, and [the style
guide](style-guide.md) is the measurement behind each threshold.

## Why the two scripts talk to each other

A figure on matplotlib's default `tab10` cycle, with a `twinx` second axis,
returned nothing but passing rows from the composition checks. `check_palette.py`
rated that same cycle's orange and green at dE 2.4 under protanopia: one hue to
that reader, against a floor of 10.5. The composition checker had no access to
the colors it was drawing.

`check_series_color` closes that. It reads the hues off the figure's own
artists, decides from the mark types whether the figure needs adjacent
separation (lines, bars) or all-pairs separation (scatter), and runs them
through the palette gates. That is row 12 of the 21.

The two checkers remain separate files because their contracts differ. The
palette checker takes hex strings on the command line and imports nothing
outside the standard library, so a non-Python toolchain can gate a palette
without a Python interpreter on PATH; the figure checker renders a matplotlib
figure, which is a Python object by definition. The figure checker imports the
palette checker, never the other way around, and the style-sheet gate reads the
same `figure.mplstyle` that ships with both.

## The backend, and why the answer used to change

You do not have to set the backend for the numbers to come out right. The
checker normalises for this itself; it did not always.

A HiDPI GUI backend, macosx on a Retina display or Qt on a scaled desktop, sets
`fig.dpi` to the authored dpi times the display's device pixel ratio at the
moment the figure is created. A figure built under one arrives at the checker
at 2×. Through 0.1.1 that meant two wrong answers at once: text extents come
back in physical pixels while the canvas reports its width in logical ones, so
the clipping gate compared 2× coordinates against a 1× bound and failed labels
that fit; and thresholds calibrated in pixels covered half the distance they
were calibrated for. The same figure passed under Agg and failed under macosx.

Since 0.1.2 the checker measures on Agg regardless of what the figure was built
under, so the verdict is a property of the figure rather than of the display.
0.8.0 finished the job: the display's pixel ratio was only ever the loud case of
a pixel threshold read against a resolution nobody had pinned, so the canvas is
now drawn at `MEASURE_DPI = 150` whatever the figure was authored at, and the
figure is handed back on the dpi it arrived on. Setting `figure.dpi` yourself no
longer moves a verdict either. `savefig.dpi` is untouched, so what you write out
is still your choice.

The bug never reached CI. Every test and every example pins Agg, so nothing in
the suite could construct the failing condition, and it stayed green across a
release.

## The gate that catches people

Type size is measured on the printed page, not on the canvas. A figure authored
at 14 inches (1008pt) and placed on a 750pt slide renders at 750/1008 = 0.74x,
so a 9pt label arrives at 6.7pt, under the 7.5pt floor, and under it by an
amount no one notices on a monitor. `page_scale` derives that ratio per figure
and the type gate measures what renders, so sizes set through rcParams or by a
helper are caught along with the ones set inline.

Placing at a fraction of the content width changes the ratio again:
`audit(fig, placed_frac=0.48)` mirrors `\includegraphics[width=0.48\textwidth]`,
and without it a half-width figure is certified at twice the type size it
ships at. For a venue in the table, `audit(fig, venue="neurips")` supplies the
width; `python check_figure.py --venues` prints all twelve with their content
widths in points.

## What a passing run does not mean

Every check is an elimination gate: each one forbids a single enumerated
failure, and none looks at the figure as a whole. 21 passing rows means the
figure avoids 21 named defects, not that the figure is good. The checker
cannot see an arrow pointing at the wrong object, a reading order that runs
backwards, or a label that is true of the concept and false of the curve
beside it. Render it and look at it.

A row can also be reporting the checker rather than the figure. Every gate runs
inside its own exception handler, so one that raises keeps its row and puts the
exception in the detail, marked as a defect in the checker rather than in the
figure. It takes its own severity: an advisory that crashed warns, a hard gate
that crashed fails, because a gate that measured nothing has not cleared the
figure. No gate is known to raise. Twenty adversarial figures, including 3D, polar,
all-NaN, infinite and zero-sized ones, found none. The handler is there anyway:
these gates read matplotlib internals that are free to move, and the version
floor they are written against has no ceiling above it.

Two blind spots remain, because a passing row looks the same as an absent one.
The colormap gate reads a `Colormap`'s name to tell an encoding from a
hand-set list of colors, so a map matplotlib left unnamed is skipped rather
than judged. It also needs `check_palette.py` importable beside it; without it
the row says it classified nothing, and passes. Both are deliberate: the row
can pass by having seen nothing.

The rules also do not transfer to interactive web charts, where hover,
responsive reflow and dark mode change most of the constraints.

**What the evidence for these gates actually is.** The colour gates answer to an
independent implementation: `tests/test_colour_space_oracle.py` runs this
project's CIECAM02 against colorspacious and its whole decision against the
same, at 0.988 specificity. The composition gates have no equivalent oracle,
because there is no importable corpus of published figures: journals ship PDFs,
not `Figure` objects. The nearest external material that exists is matplotlib's
own 28 shipped style sheets, and `tests/test_external_style_corpus.py` runs
three neutral figures under every one of them. Four of those styles are
published by their authors as accessible under colour vision deficiency, and the
colour gate rejects none of the four while rejecting 21 of the 24 that make no
such claim.

The same sweep names what does *not* discriminate, which is the more useful half:
`check_style_sheet` and `check_fonts` fire on 28 styles out of 28. The first asks
whether this project's sheet is in effect and the second asks for Type 42
embedding, and on anyone else's sheet both answers are known in advance. Both are
advisory, and neither is evidence of anything about a figure.

## Design notes

???+ note "Use what matplotlib ships"

    viridis for sequential, `RdBu` for diverging, `okabe_ito` for categorical,
    style sheets for defaults, `constrained_layout` for layout. Earlier versions
    hand-rolled all four and each was worse: `RdBu`'s poles clear every gate in
    `check_palette.py` unmodified, and a windowed custom ramp discarded 35% of
    viridis for no measured gain.

???+ note "Pixels are measured at one resolution, `MEASURE_DPI = 150`"

    Roughly half the thresholds are pixel counts: the edge window the
    readability gate uses to tell a mark from ground, the footprint below which
    a text box is a glyph or two, the distance from the page colour at which a
    pixel counts as ink. A pixel count is a measurement only if the resolution
    is fixed. `figure.dpi` is not fixed: it is an author's knob, it is whatever
    sheet is in effect, and a GUI backend multiplies it by the display's device
    pixel ratio without asking. So `audit` draws at `MEASURE_DPI` whatever the
    figure was authored at, and hands the figure back on the dpi it arrived on.

    The cost of not doing this was measured before the constant existed: across
    100/150/200/300/600 dpi, the eleven gallery figures moved 34 rows and
    flipped one. The same figure, five verdicts, from a knob that has nothing
    to do with whether it reads. `savefig.dpi` is unaffected, so what you write
    out is still yours to choose.

???+ note "WARN is not FAIL"

    Eight of the 21 rows are advisory, in that they can return `"warn"` but
    never `False`, and `ADVISORY_GATES` in `check_figure.py` is the list. A
    sub-3:1 hue is legal when it carries a direct label; a heatmap panel
    legitimately measures 0.98 ink coverage. Failing those would train people to
    ignore the row. Type size is the one row that does both: it fails under the
    floor, and warns on a figure placed under 35% of the content width.

???+ note "A row's detail carries two marks, and they mean different things"

    [FIX] introduces an action, and nothing else is allowed to wear it. [WHY]
    introduces the reason the row fired: the published floor, the perceptual
    fact, what a reader loses. A detail may carry both, in that order, and the
    fix mark is where `check_colormap` cuts when it quotes a palette row inside
    its own message.

        under 1.0pt on page at scale 0.50: ['a stroke at 0.40pt']
          [FIX] set linewidth to at least 2.00 at this scale
          [WHY] SIAM: lines thinner than one point break up or disappear in print

    Every gate but `check_collisions` names a fix; that one names the two
    colliding strings and stops, because which of the pair is free to move is a
    fact about the layout it cannot see. A reason never appears without a fix
    beside it, and that rule has a history. The two marks were one mark, an
    arrow, that said nothing about which of the two things followed it, and six
    clauses wore it while naming only why: `check_banking` cited Cleveland,
    `check_line_weight` cited SIAM, and neither told anyone what to change.
    Splitting an arrow against a tilde would have put the whole distinction on
    one glyph in a wall of detail text, so the marks are words.

???+ note "Gates are tested for their ability to fail"

    The suite is 1640 tests, and each check has one asserting it catches a
    figure with exactly that defect. The style sheet has its own tests because
    `#` starts a comment in matplotlib's style format: `grid.color: #e1e0d9`
    parses as an empty value, matplotlib keeps its default, and every other test
    stays green.

The full reasoning, meaning the measurements behind each threshold and the
rules that were tried and reverted, is in [the style guide](style-guide.md).

Which *form* the data wants is the decision no styling rule rescues, and it is
in [choosing a form](choosing-a-form.md), built on Cleveland & McGill's ordering
of the elementary perceptual tasks. Only its mechanical subset is gated: a
script can rule out a pie or a truncated bar baseline, but it cannot tell you a
box plot is hiding an n of 8.