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

import argparse
import itertools
import math

# --- color conversion -------------------------------------------------------


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(h):
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected 6-digit hex, got {h!r}")
    return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def linear_to_oklab(rgb):
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


def relative_luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(hex_a, hex_b):
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


def simulate(rgb, kind):
    m = CVD[kind]
    return tuple(max(0.0, min(1.0, sum(m[i][j] * rgb[j] for j in range(3)))) for i in range(3))


def delta_e(rgb_a, rgb_b):
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
    sign = 1 if sum(1 for s in steps if s > 0) > len(steps) / 2 else -1
    return sum(abs(s) for s in steps if s * sign < 0) / span


def cmap_back_travel(samples):
    return _back_travel([linear_to_oklab(hex_to_linear(h))[0] for h in samples])


def cmap_kind(samples):
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


def check(colors, surface="#ffffff", all_pairs=False, ordinal=False, ink=frozenset()):
    """Gate a palette. Returns `(rows, ok)`.

    Note the order: `check_figure.audit` returns its pair the other way round,
    as `(ok, rows)`. Unpacking either one the wrong way binds a bool to the
    rows and raises nothing, so the README states both and this says it where
    the call is written.

    `rows` are `(name, status, detail)`, one per gate, with `status` True or
    False. `ok` is False when any row is.

    `colors` are hex strings. `surface` is the page they are drawn on and sets
    what the contrast row measures against. `all_pairs` gates every pair rather
    than adjacent ones, which is what a scatter needs and a line chart does
    not. `ordinal` swaps the categorical separation rows for the ramp rows:
    monotone lightness, even steps, a light end that still holds contrast.
    `ink` names colours to treat as furniture rather than data.
    """
    lin = [hex_to_linear(c) for c in colors]
    lab = [linear_to_oklab(v) for v in lin]
    rows, ok = [], True

    if ordinal:
        ls = [v[0] for v in lab]
        mono = all(x > y for x, y in zip(ls, ls[1:])) or all(x < y for x, y in zip(ls, ls[1:]))
        rows.append(("Lightness monotone", mono, "steps read light->dark" if mono
                     else "steps are not monotone in lightness"))
        gaps = [abs(x - y) for x, y in zip(ls, ls[1:])]
        gap_ok = all(g >= 0.06 for g in gaps)
        rows.append(("Adjacent dL", gap_ok,
                     f"min gap {min(gaps):.3f}" if gaps else "single step"))
        light_end = max(colors, key=lambda c: linear_to_oklab(hex_to_linear(c))[0])
        cr = contrast(light_end, surface)
        rows.append(("Light-end contrast", cr >= 2.0, f"{light_end} at {cr:.2f}:1 vs surface"))
        # Step uniformity replaced an earlier "Single hue" gate (hue spread <= 20
        # degrees). That gate was a proxy for the property actually wanted, and it
        # rejected perceptually uniform multi-hue ramps such as viridis while
        # accepting a single-hue ramp with wildly uneven steps. What makes a ramp
        # readable is monotone lightness in even increments, which the three rows
        # above plus this one measure directly. The rainbow failure mode the old
        # gate was aimed at (jet) is caught by "Lightness monotone".
        ratio = max(gaps) / min(gaps) if gaps and min(gaps) > 0 else float("inf")
        rows.append(("Step uniformity", ratio <= 2.0,
                     f"largest/smallest dL {ratio:.2f}" if gaps else "single step"))
        return rows, all(r[1] for r in rows)

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
    worst_cvd, worst_cvd_at = float("inf"), None
    for i, j in pairs:
        for kind in ("protan", "deutan"):
            d = delta_e(simulate(lin[i], kind), simulate(lin[j], kind))
            if d < worst_cvd:
                worst_cvd, worst_cvd_at = d, (colors[i], colors[j], kind)
    worst_tri = min((delta_e(simulate(lin[i], "tritan"), simulate(lin[j], "tritan"))
                     for i, j in pairs), default=float("nan"))
    if worst_cvd_at:
        a, b, kind = worst_cvd_at
        good = worst_cvd >= CVD_TARGET
        rows.append((f"CVD separation ({label})", good,
                     f"worst {a} vs {b} dE {worst_cvd:.1f} ({kind}) - tritan {worst_tri:.1f}"
                     + ("" if good else "  <- needs direct labels/gaps/texture, or re-step")))

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
                     + ("" if good else f"  <- below {NORMAL_FLOOR}, hard to tell apart in full color")))

    # Advisory, not a gate: a sub-3:1 hue is legal, it just obligates a visible
    # direct label. Reporting it as FAIL while the run still passes reads as a
    # contradiction, so it carries its own status.
    low = [(c, round(contrast(c, surface), 2)) for c in colors if contrast(c, surface) < CONTRAST_MIN]
    rows.append(("Contrast vs surface", "warn" if low else True,
                 f"all >= {CONTRAST_MIN}:1" if not low
                 else f"under {CONTRAST_MIN}:1, each needs a visible direct label: {low}"))

    ok = all(r[1] is True for r in rows if r[1] != "warn")
    return rows, ok


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
    rows, ok = check(colors, a.surface, a.pairs == "all", a.ordinal, ink_set)

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
