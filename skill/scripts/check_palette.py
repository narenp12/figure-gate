"""Self-contained palette validator. No dependencies beyond the standard library.

Checks a set of hex colors against the gates a figure palette has to clear:
lightness band, chroma floor, colorblind separation, normal-vision separation,
and contrast against the surface.

    python check_palette.py "#E69F00,#56B4E9"
    python check_palette.py "#E69F00,#56B4E9,#009E73" --pairs all
    python check_palette.py "#471365,#2c718e,#44bf70" --ordinal
    python check_palette.py "#E69F00,#56B4E9" --surface "#f4f1ea"
    python check_palette.py "#0072B2,#52514e" --ink "#52514e"

Separations are OKLab dE x100. Adjacent mode checks consecutive pairs only,
which is what lines, bars and stacked marks need. `--pairs all` checks every
pair, which is what scatter, bubble and small multiples need.

Ink/neutral hexes passed with `--ink` are exempt from the lightness-band and
chroma-floor checks (an ink token is not a series hue, so the chroma rule should
not apply). They are still counted for CVD/normal separation and contrast against
the surface, mirroring `check_figure`'s own `INK_TOKENS` intent.
"""

from __future__ import annotations

import argparse
import itertools
import math
from collections.abc import Collection, Sequence

# --- color conversion -------------------------------------------------------


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(h: str) -> tuple[float, float, float]:
    """A `#rrggbb` string as linear-light RGB, each channel in 0..1.

    Linear light, not the 0..255 the hex digits carry: every distance and
    luminance below is defined on it, and averaging or mixing gamma-encoded
    values is the usual source of a wrong answer that looks plausible.

    Args:
        h: A `#rrggbb` string. The leading `#` is optional.

    Returns:
        `(r, g, b)`, each channel linear-light in 0..1.
    """
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected 6-digit hex, got {h!r}")
    return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def linear_to_oklab(rgb: Sequence[float]) -> tuple[float, float, float]:
    """Linear-light RGB as OKLab `(L, a, b)`.

    OKLab rather than CIELAB because its lightness tracks perceived lightness
    across hues, which is what every gate here asks about. `l, m, s` below are
    the cone responses the published matrix names, not a lint slip.

    Args:
        rgb: Linear-light `(r, g, b)`, each channel in 0..1.

    Returns:
        `(L, a, b)` in OKLab. `L` is 0..1.
    """
    r, g, b = rgb
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def relative_luminance(rgb: Sequence[float]) -> float:
    """WCAG relative luminance of linear-light RGB.

    The WCAG coefficients, and deliberately not OKLab's `L`: the contrast
    ratios this project cites are defined against this number, so computing
    them from a perceptual lightness would report figures no standard backs.

    Args:
        rgb: Linear-light `(r, g, b)`, each channel in 0..1.

    Returns:
        Relative luminance in 0..1, by the WCAG coefficients.
    """
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(hex_a: str, hex_b: str) -> float:
    """WCAG contrast ratio between two hex colours, from 1.0 to 21.0.

    The floors it is compared against: 4.5 for text, 3.0 for a hue against the
    surface it sits on.

    Args:
        hex_a: A `#rrggbb` string.
        hex_b: The colour to measure it against.

    Returns:
        The ratio, 1.0 (identical) to 21.0 (black on white).
    """
    la, lb = relative_luminance(hex_to_linear(hex_a)), relative_luminance(hex_to_linear(hex_b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --- colorblind simulation (Vienot, Brettel & Mollon 1999, on linear RGB) ----

CVD = {
    "protan": ((0.11238, 0.88762, 0.0),
               (0.11238, 0.88762, 0.0),
               (0.00401, -0.00401, 1.0)),
    "deutan": ((0.29275, 0.70725, 0.0),
               (0.29275, 0.70725, 0.0),
               (-0.02234, 0.02234, 1.0)),
    "tritan": ((1.0, 0.14461, -0.14461),
               (0.0, 0.85659, 0.14341),
               (0.0, 0.85659, 0.14341)),
}


def simulate(rgb: Sequence[float], kind: str) -> tuple[float, float, float]:
    """Linear-light RGB as a `"protan"`, `"deutan"` or `"tritan"` viewer sees it.

    Vienot, Brettel & Mollon (1999), applied on linear light. Protan and deutan
    are what the gates decide on; the tritan matrix is validated only for the
    red-green forms, so its distances are printed and never gated.

    Args:
        rgb: Linear-light `(r, g, b)`, each channel in 0..1.
        kind: `"protan"`, `"deutan"` or `"tritan"`.

    Returns:
        Linear-light `(r, g, b)` as that viewer sees it.
    """
    m = CVD[kind]
    r, g, b = (max(0.0, min(1.0, sum(m[i][j] * rgb[j] for j in range(3))))
               for i in range(3))
    return r, g, b


# --- anomalous trichromacy (Machado, Oliveira & Fernandes 2009) --------------
#
# The matrices above model dichromacy: a cone class absent. Most colour vision
# deficiency is not that. Anomalous trichromacy - a cone whose peak sensitivity
# is shifted rather than missing - is the more common form, and simulating only
# the endpoint would be sound if the endpoint were the worst case. It is not.
# Measured over 240000 pairs of hues this file would accept as series slots,
# 0.87% clear CVD_TARGET under dichromacy and miss it at some lower severity,
# and dichromacy overstates separation by up to 10.5 dE.
#
# Published as Table 1 of Machado, Oliveira & Fernandes (2009), at severities in
# tenths. Keyed by tenths so the lookup is an integer: severity 0.0 is the
# identity and needs no matrix.
#
# Protan and deutan only. The repository already reports tritan without gating
# it, and this model's own reference implementation notes that it does not do
# tritanopia well, so shipping a tritan severity table here would be spending
# credibility on the one form neither model is validated for.
#
# Applied on linear light, like `simulate`. The published table does not state a
# transfer function, and the domain was settled by measurement rather than by
# assumption: Machado calibrates severity 1.0 against the same Brettel/Vienot
# dichromacy this file uses, and on 4000 random hues the severity-1.0 matrices
# reproduce it to a mean dE of 2.84 (protan) and 2.44 (deutan) when applied to
# linear light, against 3.89 and 4.97 when applied to gamma-encoded sRGB.
MACHADO = {
    "protan": {
        1: (( 0.856167,  0.182038, -0.038205),
            ( 0.029342,  0.955115,  0.015544),
            (-0.002880, -0.001563,  1.004443)),
        2: (( 0.734766,  0.334872, -0.069637),
            ( 0.051840,  0.919198,  0.028963),
            (-0.004928, -0.004209,  1.009137)),
        3: (( 0.630323,  0.465641, -0.095964),
            ( 0.069181,  0.890046,  0.040773),
            (-0.006308, -0.007724,  1.014032)),
        4: (( 0.539009,  0.579343, -0.118352),
            ( 0.082546,  0.866121,  0.051332),
            (-0.007136, -0.011959,  1.019095)),
        5: (( 0.458064,  0.679578, -0.137642),
            ( 0.092785,  0.846313,  0.060902),
            (-0.007494, -0.016807,  1.024301)),
        6: (( 0.385450,  0.769005, -0.154455),
            ( 0.100526,  0.829802,  0.069673),
            (-0.007442, -0.022190,  1.029632)),
        7: (( 0.319627,  0.849633, -0.169261),
            ( 0.106241,  0.815969,  0.077790),
            (-0.007025, -0.028051,  1.035076)),
        8: (( 0.259411,  0.923008, -0.182420),
            ( 0.110296,  0.804340,  0.085364),
            (-0.006276, -0.034346,  1.040622)),
        9: (( 0.203876,  0.990338, -0.194214),
            ( 0.112975,  0.794542,  0.092483),
            (-0.005222, -0.041043,  1.046265)),
        10: (( 0.152286,  1.052583, -0.204868),
             ( 0.114503,  0.786281,  0.099216),
             (-0.003882, -0.048116,  1.051998)),
    },
    "deutan": {
        1: (( 0.866435,  0.177704, -0.044139),
            ( 0.049567,  0.939063,  0.011370),
            (-0.003453,  0.007233,  0.996220)),
        2: (( 0.760729,  0.319078, -0.079807),
            ( 0.090568,  0.889315,  0.020117),
            (-0.006027,  0.013325,  0.992702)),
        3: (( 0.675425,  0.433850, -0.109275),
            ( 0.125303,  0.847755,  0.026942),
            (-0.007950,  0.018572,  0.989378)),
        4: (( 0.605511,  0.528560, -0.134071),
            ( 0.155318,  0.812366,  0.032316),
            (-0.009376,  0.023176,  0.986200)),
        5: (( 0.547494,  0.607765, -0.155259),
            ( 0.181692,  0.781742,  0.036566),
            (-0.010410,  0.027275,  0.983136)),
        6: (( 0.498864,  0.674741, -0.173604),
            ( 0.205199,  0.754872,  0.039929),
            (-0.011131,  0.030969,  0.980162)),
        7: (( 0.457771,  0.731899, -0.189670),
            ( 0.226409,  0.731012,  0.042579),
            (-0.011595,  0.034333,  0.977261)),
        8: (( 0.422823,  0.781057, -0.203881),
            ( 0.245752,  0.709602,  0.044646),
            (-0.011843,  0.037423,  0.974421)),
        9: (( 0.392952,  0.823610, -0.216562),
            ( 0.263559,  0.690210,  0.046232),
            (-0.011910,  0.040281,  0.971630)),
        10: (( 0.367322,  0.860646, -0.227968),
             ( 0.280085,  0.672501,  0.047413),
             (-0.011820,  0.042940,  0.968881)),
    },
}


# The severities the gates sweep. 1.0 is left out on purpose: it is dichromacy,
# which `simulate` already covers with the matrices the documented numbers were
# measured on, and reading it twice under two models would move every published
# figure in the style guide for no coverage gained.
ANOMALOUS_SEVERITIES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


def simulate_anomalous(rgb: Sequence[float], kind: str,
                       severity: float) -> tuple[float, float, float]:
    """Linear-light RGB as an anomalous trichromat of this severity sees it.

    `kind` is `"protan"` or `"deutan"`. `severity` runs 0.0 (normal vision) to
    1.0 (dichromacy) and is read at the nearest tenth, which is where Machado,
    Oliveira & Fernandes publish the table. No interpolation between two
    published matrices, because that is a modelling claim the paper does not
    make and this file would then be asserting.

    `simulate` remains the dichromacy model and the anchor for every number the
    style guide quotes. This is the range between the two ends, which is where
    most colour vision deficiency actually sits.

    Args:
        rgb: Linear-light `(r, g, b)`, each channel in 0..1.
        kind: `"protan"` or `"deutan"`.
        severity: 0.0 (normal vision) to 1.0 (dichromacy), read at the
            nearest tenth.

    Returns:
        Linear-light `(r, g, b)` as that viewer sees it.
    """
    if kind not in MACHADO:
        raise ValueError(f"severity is modelled for protan and deutan only, "
                         f"not {kind!r} - see the note above MACHADO")
    if not 0.0 <= severity <= 1.0:
        raise ValueError(f"severity runs 0.0 to 1.0, got {severity!r}")
    tenths = int(round(severity * 10))
    if tenths == 0:
        r, g, b = (max(0.0, min(1.0, c)) for c in rgb)
        return r, g, b
    m = MACHADO[kind][tenths]
    r, g, b = (max(0.0, min(1.0, sum(m[i][j] * rgb[j] for j in range(3))))
               for i in range(3))
    return r, g, b


def delta_e(rgb_a: Sequence[float], rgb_b: Sequence[float]) -> float:
    """OKLab distance between two linear-light colours, x100.

    Scaled by 100 so the thresholds read as whole numbers: `CVD_TARGET = 8.0`
    for two hues under a simulation, `NORMAL_FLOOR = 15.0` in full colour.

    Args:
        rgb_a: Linear-light `(r, g, b)`.
        rgb_b: The colour to measure it against.

    Returns:
        OKLab euclidean distance, x100.
    """
    a, b = linear_to_oklab(rgb_a), linear_to_oklab(rgb_b)
    return 100 * math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# --- colormap kind ----------------------------------------------------------

CMAP_SAMPLES = 256
CMAP_QUALITATIVE_N = 40
CMAP_SPAN_MIN = 0.02
CMAP_BACKTRAVEL_MAX = 0.02
CMAP_WRAP_DE_MAX = 3.0


def _back_travel(ls):
    steps = [b - a for a, b in zip(ls, ls[1:])]
    if not steps:
        return 0.0
    span = max(ls) - min(ls)
    if span <= 0:
        return 0.0
    # Direction is net travel, not a majority vote over the steps. A vote counts
    # plateau steps against ascending, and 8-bit sRGB rounding makes plateaus the
    # majority whenever the lightness span is narrow relative to the sample count:
    # viridis windowed to t in [0.00, 0.38], the window the style guide asks for,
    # is 158 plateaus out of 255 steps. Voting reads that ramp as descending and
    # scores every genuine rise as back travel, 1.00 against a 0.02 threshold.
    sign = 1 if ls[-1] >= ls[0] else -1
    return sum(abs(s) for s in steps if s * sign < 0) / span


def cmap_back_travel(samples: Sequence[str]) -> float:
    """How much of a ramp's lightness runs backwards, as a fraction of its span.

    0.0 is monotone. `CMAP_BACKTRAVEL_MAX = 0.02` is where a ramp stops
    counting as ordered, because lightness that reverses makes two different
    values render at the same lightness.

    Args:
        samples: Hex strings sampled along the ramp, in ramp order.

    Returns:
        Backward lightness travel as a fraction of the ramp's span. 0.0 is
        monotone.
    """
    return _back_travel([linear_to_oklab(hex_to_linear(h))[0] for h in samples])


def cmap_kind(samples: Sequence[str]) -> str:
    """Classify hex samples as `qualitative`, `sequential`, `diverging`,
    `cyclic` or `misc`.

    `misc` is the failure: the lightness reverses, or its span is flat, or its
    halves are monotone and its ends match neither cyclic nor diverging. A
    colormap in that state encodes nothing the reader can order.

    Fewer than `CMAP_QUALITATIVE_N = 40` samples is read as a set of category
    colours rather than a ramp, and gated on separation instead.

    Args:
        samples: Hex strings sampled along the colormap, in order.

    Returns:
        One of `"qualitative"`, `"sequential"`, `"diverging"`, `"cyclic"` or
        `"misc"`.
    """
    if len(samples) < CMAP_QUALITATIVE_N:
        return "qualitative"

    ls = [linear_to_oklab(hex_to_linear(h))[0] for h in samples]

    if max(ls) - min(ls) < CMAP_SPAN_MIN:
        return "misc"

    if _back_travel(ls) < CMAP_BACKTRAVEL_MAX:
        return "sequential"

    half = len(ls) // 2
    if (_back_travel(ls[:half + 1]) < CMAP_BACKTRAVEL_MAX
            and _back_travel(ls[half:]) < CMAP_BACKTRAVEL_MAX):
        wrap = delta_e(hex_to_linear(samples[0]), hex_to_linear(samples[-1]))
        return "cyclic" if wrap < CMAP_WRAP_DE_MAX else "diverging"

    return "misc"


# --- gates ------------------------------------------------------------------

L_MIN, L_MAX = 0.43, 0.77
CHROMA_MIN = 0.10
CVD_TARGET = 8.0          # below this, secondary encoding is mandatory
NORMAL_FLOOR = 15.0       # hard floor; no secondary encoding excuses this
CONTRAST_MIN = 3.0        # for marks; text on a fill needs 4.5 (3.0 if large)

# The three ordinal rows. `--ordinal` swaps the categorical gates for these, and
# all three ran on literals inside `check` while every categorical threshold sat
# up here, so half the validator was tunable and half was not.
ORDINAL_DL_MIN = 0.06     # OKLab lightness between adjacent steps
ORDINAL_LIGHT_END_CONTRAST_MIN = 2.0   # lightest step against the surface
ORDINAL_STEP_RATIO_MAX = 2.0           # largest lightness step / smallest


def check(colors: Sequence[str], surface: str = "#ffffff",
          all_pairs: bool = False, ordinal: bool = False,
          ink: Collection[str] = frozenset(),
          ) -> tuple[bool, list[tuple[str, bool | str, str]]]:
    """Gate a palette. Returns `(ok, rows)`.

    The order matches `check_figure.audit`. It did not until 0.4.0: this
    returned `(rows, ok)` and the README carried a paragraph warning about the
    difference, which is documentation standing in for a fix. Unpacking either
    one the wrong way binds a bool to the rows and raises nothing, so the two
    were made the same rather than described.

    `rows` are `(name, status, detail)`, one per gate. `status` is True,
    False, or the string "warn" for the advisory contrast row, and only a
    hard False sets `ok` to False.

    `colors` are hex strings. `surface` is the page they are drawn on and sets
    what the contrast row measures against. `all_pairs` gates every pair rather
    than adjacent ones, which is what a scatter needs and a line chart does
    not. `ordinal` swaps the categorical separation rows for the ramp rows:
    monotone lightness, even steps, a light end that still holds contrast.
    `ink` names colours to treat as furniture rather than data.

    Args:
        colors: Hex strings, the palette to gate.
        surface: The page colour they are drawn on.
        all_pairs: Gate every pair rather than adjacent ones.
        ordinal: Swap the categorical rows for the ramp rows.
        ink: Colours to treat as furniture rather than data.

    Returns:
        `(ok, rows)`. `rows` are `(name, status, detail)`, one per gate;
        `status` is True, False or "warn", and `ok` is False only when a
        row is a hard False.
    """
    lin = [hex_to_linear(c) for c in colors]
    lab = [linear_to_oklab(v) for v in lin]
    rows: list[tuple[str, bool | str, str]] = []
    ok = True

    if ordinal:
        ls = [v[0] for v in lab]
        mono = all(x > y for x, y in zip(ls, ls[1:])) or all(x < y for x, y in zip(ls, ls[1:]))
        rows.append(("Lightness monotone", mono, "steps read light->dark" if mono
                     else "steps are not monotone in lightness"))
        gaps = [abs(x - y) for x, y in zip(ls, ls[1:])]
        gap_ok = all(g >= ORDINAL_DL_MIN for g in gaps)
        rows.append(("Adjacent dL", gap_ok,
                     f"min gap {min(gaps):.3f}" if gaps else "single step"))
        light_end = max(colors, key=lambda c: linear_to_oklab(hex_to_linear(c))[0])
        cr = contrast(light_end, surface)
        rows.append(("Light-end contrast", cr >= ORDINAL_LIGHT_END_CONTRAST_MIN,
                     f"{light_end} at {cr:.2f}:1 vs surface"))
        # Step uniformity replaced an earlier "Single hue" gate (hue spread <= 20
        # degrees). That gate was a proxy for the property actually wanted, and it
        # rejected perceptually uniform multi-hue ramps such as viridis while
        # accepting a single-hue ramp with wildly uneven steps. What makes a ramp
        # readable is monotone lightness in even increments, which the three rows
        # above plus this one measure directly. The rainbow failure mode the old
        # gate was aimed at (jet) is caught by "Lightness monotone".
        ratio = max(gaps) / min(gaps) if gaps and min(gaps) > 0 else float("inf")
        rows.append(("Step uniformity", ratio <= ORDINAL_STEP_RATIO_MAX,
                     f"largest/smallest dL {ratio:.2f}" if gaps else "single step"))
        return all(r[1] for r in rows), rows

    ink_set = set(ink) if isinstance(ink, frozenset) else set(ink)
    band = [c for c, v in zip(colors, lab)
            if c not in ink_set and not (L_MIN <= v[0] <= L_MAX)]
    n_exempt_band = sum(1 for c in colors if c in ink_set and
                        not (L_MIN <= linear_to_oklab(hex_to_linear(c))[0] <= L_MAX))
    rows.append(("Lightness band", not band,
                 f"all {len(colors)} inside L {L_MIN}-{L_MAX}" if not band
                 else f"outside: {band}"
                 + (f" ({n_exempt_band} ink tokens exempted)" if n_exempt_band else "")))

    chroma = [c for c, v in zip(colors, lab)
              if c not in ink_set and math.hypot(v[1], v[2]) < CHROMA_MIN]
    n_exempt_chroma = sum(1 for c in colors if c in ink_set and
                          math.hypot(*linear_to_oklab(hex_to_linear(c))[1:]) < CHROMA_MIN)
    rows.append(("Chroma floor", not chroma,
                 f"all {len(colors)} >= {CHROMA_MIN}" if not chroma
                 else f"too gray: {chroma}"
                 + (f" ({n_exempt_chroma} ink tokens exempted)" if n_exempt_chroma else "")))

    pairs = (list(itertools.combinations(range(len(colors)), 2)) if all_pairs
             else [(i, i + 1) for i in range(len(colors) - 1)])
    label = "all-pairs" if all_pairs else "adjacent"

    # Gate on protanopia and deuteranopia (~8% of males between them). Tritan is
    # reported but not gated: it is ~0.01% prevalence, and the Vienot matrix used
    # here is only validated for the red-green forms, so a tritan number is
    # indicative rather than decisive.
    #
    # Swept over severity, not read at the endpoint. Dichromacy is not the worst
    # case: measured over 240000 pairs of hues this file would accept as series
    # slots, 0.87% clear CVD_TARGET at dichromacy and miss it at some lower
    # severity. See MACHADO.
    worst_cvd, worst_cvd_at = float("inf"), None
    for i, j in pairs:
        for kind in ("protan", "deutan"):
            views = [(delta_e(simulate(lin[i], kind), simulate(lin[j], kind)),
                      1.0)]
            views += [(delta_e(simulate_anomalous(lin[i], kind, s),
                               simulate_anomalous(lin[j], kind, s)), s)
                      for s in ANOMALOUS_SEVERITIES]
            d, at = min(views)
            if d < worst_cvd:
                worst_cvd, worst_cvd_at = d, (colors[i], colors[j], kind, at)
    worst_tri = min((delta_e(simulate(lin[i], "tritan"), simulate(lin[j], "tritan"))
                     for i, j in pairs), default=float("nan"))
    if worst_cvd_at:
        a, b, kind, at = worst_cvd_at
        good = worst_cvd >= CVD_TARGET
        rows.append((f"CVD separation ({label})", good,
                     f"worst {a} vs {b} dE {worst_cvd:.1f} ({kind} at severity "
                     f"{at:.1f}) - tritan {worst_tri:.1f}"
                     + ("" if good else "  [FIX] needs direct labels/gaps/texture, or re-step")))

    worst_n, worst_n_at = float("inf"), None
    for i, j in pairs:
        d = delta_e(lin[i], lin[j])
        if d < worst_n:
            worst_n, worst_n_at = d, (colors[i], colors[j])
    if worst_n_at:
        a, b = worst_n_at
        good = worst_n >= NORMAL_FLOOR
        rows.append((f"Normal-vision floor ({label})", good,
                     f"worst {a} vs {b} dE {worst_n:.1f}"
                     + ("" if good else
                        "  [FIX] move one of the pair, or re-step the ramp"
                        f"  [WHY] below {NORMAL_FLOOR}, hard to tell apart in "
                        "full color")))

    # Advisory, not a gate: a sub-3:1 hue is legal, it just obligates a visible
    # direct label. Reporting it as FAIL while the run still passes reads as a
    # contradiction, so it carries its own status.
    low = [(c, round(contrast(c, surface), 2)) for c in colors if contrast(c, surface) < CONTRAST_MIN]
    rows.append(("Contrast vs surface", "warn" if low else True,
                 f"all >= {CONTRAST_MIN}:1" if not low
                 else f"under {CONTRAST_MIN}:1, each needs a visible direct label: {low}"))

    ok = all(r[1] is True for r in rows if r[1] != "warn")
    return ok, rows


def main():
    ap = argparse.ArgumentParser(description="Validate a figure palette.")
    ap.add_argument("colors", help="comma-separated hex colors")
    # White, because that is what `figure.mplstyle` renders and what the page
    # under it is. An earlier default of #fcfcfb described a surface no figure
    # in this project ever had, so every contrast number in the guide was
    # computed against a background that did not exist. Override it when the
    # document's page really is tinted.
    ap.add_argument("--surface", default="#ffffff", help="background the marks sit on")
    ap.add_argument("--pairs", choices=["adjacent", "all"], default="adjacent")
    ap.add_argument("--ordinal", action="store_true", help="ordered one-hue ramp")
    ap.add_argument(
        "--ink", default="",
        help="comma-separated ink/neutral hexes (exempt from chroma and lightness rules)")
    a = ap.parse_args()

    colors = [c.strip() for c in a.colors.split(",") if c.strip()]
    ink_set = frozenset(c.strip() for c in a.ink.split(",") if c.strip())
    ok, rows = check(colors, a.surface, a.pairs == "all", a.ordinal, ink_set)

    kind = "ordinal ramp" if a.ordinal else "categorical"
    print(f"\nPalette ({kind}, surface {a.surface}): {len(colors)} slots")
    warned = False
    for name, status, detail in rows:
        tag = "WARN" if status == "warn" else ("PASS" if status else "FAIL")
        warned = warned or status == "warn"
        print(f"  [{tag}] {name:<28} {detail}")
    verdict = "ALL CHECKS PASS" if ok else "FAILED - fix the marked checks"
    if ok and warned:
        verdict += " (with advisories - act on the WARN rows)"
    print(f"\n  -> {verdict}\n")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
