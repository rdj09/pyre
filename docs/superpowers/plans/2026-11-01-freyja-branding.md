# Freyja branding for the pyRE Treaty Pricing Workbench

> **How to use this file.** Save it in the pyre repo as
> `docs/superpowers/plans/2026-11-01-freyja-branding.md`, open Claude Code at the repo root and say:
> *"Implement docs/superpowers/plans/2026-11-01-freyja-branding.md. Follow it exactly and stop at
> the acceptance checks to show me the screenshots."* Everything below the line is written for
> Claude Code.

---

## Goal

Apply Freyja Consulting's brand to the Panel app in `app/`: colours, Montserrat type, the
FREYJA CONSULTING wordmark, a favicon and the company legal footer. This change covers styling
and the logo only.

The brand hierarchy is **pyRE first, with Freyja as the endorser**. The app stays
"pyRE Treaty Pricing Workbench". Freyja appears as the maintainer in the header and in the
footer.

Every design decision in this file has already been made, and the code in the reference section
was run and screenshotted against this repo at `a458cf3` with Panel 1.10.0 and Bokeh 3.10.1.
Implement it as written. If something no longer applies because the repo has moved on, carry
out the intent of the change and tell me what you changed.

## Ground rules

- **Branch:** `git switch develop && git pull --ff-only && git switch -c feature/freyja-branding`.
  Commit in logical steps (assets → styles → wiring → docs). Don't push and don't open a PR
  unless I ask.
- **Files you may touch:**
  - `app/main.py` and `run_app.py`
  - `app/pages/*.py`, for presentation only: button types and table titles and formatters
  - new files: `app/theme.py`, everything under `app/assets/`, and `scripts/build_brand_assets.py`
  - `pyproject.toml`, in the `[tool.hatch.envs.*]` tables only
  - `.gitignore`, `docs/workbench.md` and `CLAUDE.md`
- **Don't touch** `src/pyre/`, `app/service.py`, `app/state.py`, the existing tests or
  `[project] dependencies`. The core package stays dependency-free, and `service.py` and
  `state.py` stay free of Panel.
- **No behaviour changes.** Keep the same widgets, callbacks, status messages and UI copy. Only
  the look changes.
- **Light theme only.** Don't add a dark mode or a theme toggle.

## Brand rules (source of truth, so use these exact values)

| Token | Hex | Use in the app |
|---|---|---|
| Navy | `#0A2E50` | Header, table headers, all body text and headings |
| Gold | `#C9A076` | Primary buttons, the header rule, the active tab underline, focus outline. Never use it as text on a light background. |
| Off-white | `#FAF9F9` | Page background, and text on Navy |
| Slate | `#8C98A6` | Input borders and sort arrows. Never use it for text. |
| Light Blue | `#8EBED5` | The "MAINTAINED BY" eyebrow on Navy, and the info alert rule |
| Cream | `#F9F5E3` | Table banding and the warning alert background |
| White | `#FFFFFF` | Surfaces: inputs, table rows, secondary button |
| Slate Deep | `#5C6A79` | Secondary text: labels, inactive tabs, footer |
| Navy 10 | `#E6EAEE` | Hairlines and dividers |
| Gold 20 | `#F4ECE4` | Table row hover and the input focus halo |
| Light Blue 20 | `#E8F2F7` | Info alert background |
| Green / Red | `#4F7F5A` / `#A94438` | Status rules on success and danger alerts only |

- **Typeface:** Montserrat only. Use 400 for body text, 500 for labels and inactive tabs, 600 for
  headings, the title and the active tab, and 700 UPPERCASE for buttons, table headers and
  eyebrows. Line height is about 1.15 for headings and 1.5 for body text.
- **Wordmark:** "FREYJA" in Montserrat ExtraBold 800 with 0.15 em tracking, then a space, then
  "CONSULTING" in Montserrat Light 300 with no tracking. Same size, one colour: Off-white on Navy,
  or Navy on light backgrounds. Freyja has no image logo, so never redraw the mark in another
  font, make it two-tone or make it Gold.
- **Legal line, exact text:**
  `Freyja Consulting Ltd · Registered in England and Wales · Company No. 16939328 · Registered office: 320 Firecrest Court, Warrington, WA1 1RG`
- **Never use** colours outside the table above (this includes the Bootstrap and Bokeh default
  blues), gradients, drop shadows, the Google Fonts CDN, the favicon from freyja-consulting.com
  or any other image taken from the website.

## Design decisions (already made)

| Element | Treatment |
|---|---|
| Header | A flat Navy bar with a 3 px Gold bottom rule and no drop shadow. The title sits on the left in SemiBold Off-white. On the right is the eyebrow "MAINTAINED BY" (700, 0.62 rem, 0.12 em tracking, Light Blue) followed by the Off-white wordmark at 14 px tall. The eyebrow and wordmark together form one link to https://freyja-consulting.com, which opens in a new tab. |
| Favicon | A Navy rounded square with an Off-white "F" in ExtraBold (converted to outlines) above a short Gold bar. |
| Page | Off-white background, White surfaces, Navy text. Field labels are Slate Deep Medium. |
| Tabs | No boxed tabs. Inactive tabs are Slate Deep. The active tab is Navy SemiBold with a 3 px Gold underline. |
| Buttons | Each tab has one primary action: Load demo data, Save contract metadata and Run pricing. Primary buttons have a Gold fill, Navy Bold uppercase text and a 0.33 rem radius, and turn Navy with Off-white text on hover. "Add layer" becomes a secondary button (`button_type="default"`): White with a 1 px Navy border. Show a 2 px Gold outline on `:focus-visible` only. |
| Alerts | Navy text with a 4 px left rule in the status colour. Warning: Cream background with a Gold rule. Success: White with a green rule. Danger: White with a red rule. Info: Light Blue 20 with a Light Blue rule. |
| Tables | A Navy header with Off-white Bold UPPERCASE titles, using readable names passed through `titles=`. Rows band White and Cream, with Navy 10 hairlines, no vertical lines and tabular figures. Amounts use the format `0,0` and are right-aligned. Ratios and lines use `0.0%`. Years use plain `0`; today they display as "2,022". |
| Footer | Placed at the end of `main`: a hairline, then two lines of 0.75 rem Slate Deep text. The first line is `pyRE {__version__} (beta) · MIT licence · github.com/rdj09/pyre` and the second is the legal line. |
| Fonts | Self-hosted Latin-subset woff2 files for weights 400, 500, 600 and 700 in `app/assets/fonts/`, together with `OFL.txt`. They are served at `./assets` through `--static-dirs` or `pn.serve(static_dirs=…)`. The wordmark and favicon are SVGs with the text converted to outlines, so they need no font at all. |

## How Panel styling works here (read this before writing CSS)

1. **Every component renders in its own shadow DOM.** Document-level CSS (the template's
   `raw_css`) reaches only the template chrome: `body`, `#header` and the title. The `@font-face`
   rules must also live there. Component styling has to be injected into each shadow root, which
   is what `FreyjaDesign(Bootstrap)` does with
   `modifiers = {Viewable: {"stylesheets": [Inherit, "assets/freyja.css"]}}`. Relative paths
   resolve against the module that defines the class, so `app/theme.py` loads
   `app/assets/freyja.css`. Bootstrap's own modifiers, such as the Tabulator theme, are still
   inherited through the MRO.
2. **Panel's Bootstrap theme declares its variables on `:host`.** Setting `--design-*` or
   `--bs-*` on the document `:root` therefore does nothing inside components. Set them in
   `freyja.css` instead, which loads after the theme CSS.
3. **Some theme rules are more specific than a plain selector:** tabs, the Tabulator header and
   rows, and `:host(.solid)` primary buttons. The reference CSS mirrors the selectors in
   `<site-packages>/panel/theme/css/bootstrap.css` so that its rules win on source order. If your
   installed Panel version differs from 1.10 and a rule doesn't take effect, open that file and
   match its selectors. Don't reach for `!important`.
4. **`BootstrapTemplate(favicon=…)` takes a local file path**, which it embeds as base64. Pass
   the path rather than a URL.
5. **Bokeh's `NumberFormatter` left-aligns by default**, so pass `text_align="right"` for numbers.
6. **There is a pre-existing launch bug.** `panel serve app/main.py` puts `app/` on `sys.path`
   rather than the repo root, so `from app.pages …` fails with
   `ModuleNotFoundError: No module named 'app'`. This also affects `hatch run panel:serve`. Fix
   the Hatch env with `[tool.hatch.envs.panel.env-vars] PYTHONPATH = "."`, and use
   `PYTHONPATH=.` when running `panel serve` by hand. `python run_app.py` is unaffected.

## Steps

1. **Brand assets.**
   - Create `scripts/build_brand_assets.py` exactly as given in the reference section, add the
     `brand` Hatch env and add `.cache/montserrat/` to `.gitignore` (see the diff).
   - Run `hatch run brand:build`. It downloads Montserrat (SIL OFL) once from
     `raw.githubusercontent.com/JulietaUla/Montserrat`.
   - Commit everything under `app/assets/brand/` and `app/assets/fonts/`, but not `.cache/`.
   - Run the build again and confirm that `git status` shows no changes to the SVGs, which
     proves the output is deterministic.
2. **Stylesheets.** Create `app/assets/freyja.css` and `app/assets/freyja-page.css` from the
   reference.
3. **Theme module.** Create `app/theme.py` from the reference.
4. **Wiring.** Apply the changes in the diff to `app/main.py`, `app/pages/contract_config.py`,
   `app/pages/results.py`, `run_app.py`, `pyproject.toml` and `.gitignore`.
5. **Docs.**
   - In `docs/workbench.md`, update "Install and run" to cover `--static-dirs`, the `PYTHONPATH`
     note and `python run_app.py`. Add a short "Branding" section saying where the assets live,
     how to rebuild them with `hatch run brand:build`, and that colours come only from the
     tokens in `freyja.css`.
   - In `CLAUDE.md`, add `app/theme.py`, `app/assets/` and `scripts/build_brand_assets.py` to
     the workbench layout table, and add `hatch run brand:build` to the commands list.
6. **Verify.** Work through the acceptance checks below.

## Acceptance checks

1. Tests and lint:
   - `pytest -q tests/test_app_service.py` passes.
   - `pytest -q --ignore=tests/test_exposure_curve_fitting.py` still reports **22 failed, 78
     passed**, unchanged from before.
   - `ruff check app/ scripts/` and `ruff format --check app/ scripts/` are clean.
2. Colour audit: `grep -rIhoiE '#[0-9a-f]{6}\b' app/ | sort -fu` returns only hex values from the
   brand table.
3. Run `hatch run panel:serve` and also `python run_app.py`. Then confirm the following in the
   browser:
   - The header matches the design table, and the wordmark link opens freyja-consulting.com in
     a new tab.
   - The browser tab shows the "F" favicon.
   - DevTools → Network shows no 404s for `assets/…`.
   - `[...document.fonts].filter(f => f.status === "loaded")` lists Montserrat 400, 500, 600
     and 700.
4. Run through the demo:
   - Click Load demo data. A green-ruled success alert appears.
   - In "2. Configure contract", set attachment 100000 and limit 200000, then click Add layer
     and Save contract metadata. The layer table shows "100,000", "200,000" and "100.0%".
   - In "3. Run pricing", click Run pricing. The results show **2022: 0 / 150,000 / 15.0%** and
     **2023: 50,000 / 200,000 / 16.7%**. Years display without a comma.
5. If Playwright is available, screenshot each of the three tabs at 1280 × 860 and show them to
   me. Otherwise, describe what you checked.

## Out of scope

Keep these out of this change. List them for me at the end as possible follow-ups.

- The MkDocs site theme, which still uses Material teal
- README branding and the "Maintained by Freyja Consulting" line in the README and docs
- Dark mode
- UI copy edits
- Fixing the pre-existing failing tests

---

## Reference implementation (verified)

### `scripts/build_brand_assets.py`

```python
"""Build the Freyja Consulting brand assets used by the Treaty Pricing Workbench.

Outputs (committed to the repo; rerun only if the brand changes):
  app/assets/brand/freyja-wordmark-offwhite.svg   wordmark for the Navy header
  app/assets/brand/freyja-wordmark-navy.svg       wordmark for light backgrounds (README, docs)
  app/assets/brand/favicon.svg                    browser-tab icon
  app/assets/fonts/Montserrat-{400,500,600,700}.woff2   Latin-subset web fonts
  app/assets/fonts/OFL.txt                        Montserrat licence (SIL OFL 1.1)

Text in the SVGs is converted to outlines, so they render identically whether or
not Montserrat is installed. Montserrat (SIL OFL 1.1) is downloaded once from
github.com/JulietaUla/Montserrat into .cache/montserrat/ (gitignored).

    hatch run brand:build
    # or: pip install fonttools brotli uharfbuzz && python scripts/build_brand_assets.py
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

import uharfbuzz as hb
from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "app" / "assets"
CACHE = REPO / ".cache" / "montserrat"
SRC = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/"
WEIGHTS = {
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
}

NAVY, GOLD, OFFWHITE = "#0A2E50", "#C9A076", "#FAF9F9"
LATIN = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,"
    "U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
)


def fetch(rel: str, fonts_dir: Path | None) -> Path:
    name = Path(rel).name
    if fonts_dir and (fonts_dir / name).exists():
        return fonts_dir / name
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / name
    if not dest.exists():
        urllib.request.urlretrieve(SRC + rel, dest)
    return dest


def shape(path: Path, text: str, tracking_em: float = 0.0):
    """Return [(glyph_name, x_offset_units)], total advance in font units."""
    blob = hb.Blob.from_file_path(str(path))
    font = hb.Font(hb.Face(blob))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": False})
    tt = TTFont(path)
    order = tt.getGlyphOrder()
    upem = tt["head"].unitsPerEm
    x, out = 0.0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        out.append((order[info.codepoint], x + pos.x_offset))
        x += pos.x_advance + tracking_em * upem  # CSS letter-spacing: after every glyph
    return tt, out, x


def outline(runs, size_px: float) -> tuple[str, tuple[float, float, float, float]]:
    """runs: [(TTFont, [(glyph, x)], x_origin_px)] -> SVG path data and ink bounds (px)."""
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    bounds = BoundsPen(None)
    for tt, glyphs, x0 in runs:
        gs = tt.getGlyphSet()
        s = size_px / tt["head"].unitsPerEm
        pen.glyphSet = bounds.glyphSet = gs
        for name, x in glyphs:
            m = (s, 0, 0, -s, x0 + x * s, 0)  # flip y; baseline at y=0
            gs[name].draw(TransformPen(pen, m))
            gs[name].draw(TransformPen(bounds, m))
    return pen.getCommands(), bounds.bounds


def wordmark(fonts: dict[int, Path], colour: str, size_px: float = 100.0) -> str:
    bold, light = fonts[800], fonts[300]
    tt_b, g_b, adv_b = shape(bold, "FREYJA", tracking_em=0.15)
    tt_l, g_space, adv_space = shape(light, " ")
    tt_l, g_l, _ = shape(light, "CONSULTING")
    s_b = size_px / tt_b["head"].unitsPerEm
    s_l = size_px / tt_l["head"].unitsPerEm
    x_consulting = adv_b * s_b + adv_space * s_l
    d, (x0, y0, x1, y1) = outline([(tt_b, g_b, 0.0), (tt_l, g_l, x_consulting)], size_px)
    pad = size_px * 0.04
    vb = f"{x0 - pad:.2f} {y0 - pad:.2f} {x1 - x0 + 2 * pad:.2f} {y1 - y0 + 2 * pad:.2f}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" '
        f'aria-label="Freyja Consulting"><title>Freyja Consulting</title>'
        f'<path fill="{colour}" d="{d}"/></svg>\n'
    )


def favicon(fonts: dict[int, Path]) -> str:
    tt, g, adv = shape(fonts[800], "F")
    size = 44.0
    d, (x0, y0, x1, y1) = outline([(tt, g, 0.0)], size)
    w, h = x1 - x0, y1 - y0
    tx, ty = 32 - w / 2 - x0, 29 - h / 2 - y0  # optically a touch above centre
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="10" fill="{NAVY}"/>'
        f'<path fill="{OFFWHITE}" transform="translate({tx:.2f} {ty:.2f})" d="{d}"/>'
        f'<rect x="{tx + x0:.2f}" y="{ty + y1 + 4:.2f}" width="{w:.2f}" height="4" fill="{GOLD}"/>'
        "</svg>\n"
    )


def web_fonts(fonts: dict[int, Path], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for weight in (400, 500, 600, 700):
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "tnum", "lnum"]
        f = TTFont(fonts[weight])
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=subset.parse_unicodes(LATIN))
        sub.subset(f)
        f.flavor = "woff2"
        f.save(out / f"Montserrat-{weight}.woff2")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fonts-dir", type=Path, help="use local Montserrat-*.ttf instead of downloading"
    )
    args = ap.parse_args()
    fonts = {w: fetch(f"fonts/ttf/Montserrat-{n}.ttf", args.fonts_dir) for w, n in WEIGHTS.items()}
    brand = ASSETS / "brand"
    brand.mkdir(parents=True, exist_ok=True)
    (brand / "freyja-wordmark-offwhite.svg").write_text(wordmark(fonts, OFFWHITE), encoding="utf-8")
    (brand / "freyja-wordmark-navy.svg").write_text(wordmark(fonts, NAVY), encoding="utf-8")
    (brand / "favicon.svg").write_text(favicon(fonts), encoding="utf-8")
    web_fonts(fonts, ASSETS / "fonts")
    licence = fetch("OFL.txt", args.fonts_dir)
    (ASSETS / "fonts" / "OFL.txt").write_bytes(licence.read_bytes())
    for p in sorted(ASSETS.rglob("*")):
        if p.is_file():
            print(f"{p.relative_to(REPO)}  {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
```

### `app/theme.py`

```python
"""Freyja Consulting branding for the Treaty Pricing Workbench (Panel-only module).

Colours and type come from the Freyja brand guide. Do not add colours that are
not defined in app/assets/freyja.css.
"""

from __future__ import annotations

from pathlib import Path

import panel as pn
from panel.theme import Bootstrap
from panel.theme.base import Inherit
from panel.viewable import Viewable

from pyre import __about__

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
BRAND_DIR = ASSETS_DIR / "brand"

NAVY = "#0A2E50"
OFFWHITE = "#FAF9F9"

APP_TITLE = "pyRE Treaty Pricing Workbench"
FREYJA_URL = "https://freyja-consulting.com"
LEGAL_LINE = (
    "Freyja Consulting Ltd · Registered in England and Wales · Company No. 16939328 · "
    "Registered office: 320 Firecrest Court, Warrington, WA1 1RG"
)


class FreyjaDesign(Bootstrap):
    """Bootstrap design plus the Freyja stylesheet in every component's shadow root."""

    modifiers = {
        Viewable: {"stylesheets": [Inherit, "assets/freyja.css"]},
    }


def page_css() -> str:
    """Document-level CSS: @font-face rules and the template header."""
    return (ASSETS_DIR / "freyja-page.css").read_text(encoding="utf-8")


def endorsement() -> pn.pane.HTML:
    """'Maintained by FREYJA CONSULTING' for the right of the header."""
    svg = (BRAND_DIR / "freyja-wordmark-offwhite.svg").read_text(encoding="utf-8")
    return pn.pane.HTML(
        f'<a class="freyja-endorse" href="{FREYJA_URL}" target="_blank" rel="noopener" '
        f'title="freyja-consulting.com">'
        f'<span class="freyja-endorse__label">Maintained by</span>'
        f'<span class="freyja-endorse__mark">{svg}</span></a>',
        sizing_mode="stretch_width",
        margin=0,
    )


def footer() -> pn.pane.HTML:
    version = __about__.__version__
    return pn.pane.HTML(
        f'<footer class="freyja-footer">'
        f"<p>pyRE {version} (beta) · MIT licence · "
        f'<a href="https://github.com/rdj09/pyre" target="_blank" rel="noopener">'
        f"github.com/rdj09/pyre</a></p>"
        f"<p>{LEGAL_LINE}</p></footer>",
        sizing_mode="stretch_width",
    )


def branded_template(*objects) -> pn.template.BootstrapTemplate:
    template = pn.template.BootstrapTemplate(
        title=APP_TITLE,
        design=FreyjaDesign,
        header_background=NAVY,
        header_color=OFFWHITE,
        favicon=str(BRAND_DIR / "favicon.svg"),
        raw_css=[page_css()],
    )
    template.header.append(endorsement())
    template.main.extend([*objects, footer()])
    return template
```

### `app/assets/freyja.css` (component stylesheet, loaded into every shadow root)

```css
/* Freyja Consulting brand - component stylesheet.
   Loaded into every Panel component's shadow root by app.theme.FreyjaDesign.
   Only the colours below may be used. */

:host,
:root {
  --freyja-navy: #0A2E50;
  --freyja-gold: #C9A076;
  --freyja-offwhite: #FAF9F9;
  --freyja-slate: #8C98A6;
  --freyja-lightblue: #8EBED5;
  --freyja-cream: #F9F5E3;
  --freyja-white: #FFFFFF;
  --freyja-slate-deep: #5C6A79;
  --freyja-navy-10: #E6EAEE;
  --freyja-gold-20: #F4ECE4;
  --freyja-lightblue-20: #E8F2F7;
  --freyja-green: #4F7F5A;
  --freyja-red: #A94438;
  --freyja-font: "Montserrat", Arial, sans-serif;
  --freyja-radius: 0.33rem;

  /* Panel design variables */
  --design-primary-color: var(--freyja-navy);
  --design-primary-text-color: var(--freyja-offwhite);
  --design-secondary-color: var(--freyja-gold);
  --design-secondary-text-color: var(--freyja-navy);
  --design-background-color: var(--freyja-offwhite);
  --design-background-text-color: var(--freyja-navy);
  --design-surface-color: var(--freyja-white);
  --design-surface-text-color: var(--freyja-navy);

  /* Bootstrap / Bokeh variables */
  --bokeh-base-font: var(--freyja-font);
  --bs-font-sans-serif: var(--freyja-font);
  --bs-body-font-family: var(--freyja-font);
  --bs-body-color: var(--freyja-navy);
  --bs-body-bg: var(--freyja-offwhite);
  --bs-primary: var(--freyja-navy);
  --bs-primary-rgb: 10, 46, 80;
  --bs-border-color: var(--freyja-slate);
  --bs-link-color: var(--freyja-navy);
  --bs-link-hover-color: var(--freyja-navy);

  font-family: var(--freyja-font);
  color: var(--freyja-navy);
}

/* ---- Headings (Markdown panes) ---- */
h1, h2, h3, h4 {
  font-family: var(--freyja-font);
  font-weight: 600;
  line-height: 1.15;
  color: var(--freyja-navy);
}
p, li { line-height: 1.5; }
a { color: var(--freyja-navy); text-decoration: none; }
a:hover { text-decoration: underline; text-decoration-color: var(--freyja-gold); }

/* ---- Buttons: primary = Gold call to action; default = Navy outline ---- */
.bk-btn {
  font-family: var(--freyja-font);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-size: 0.8rem;
  border-radius: var(--freyja-radius);
  box-shadow: none;
}
.bk-btn.bk-btn-primary,
:host(.solid) .bk-btn.bk-btn-primary {
  --bs-btn-bg: var(--freyja-gold);
  --bs-btn-color: var(--freyja-navy);
  --bs-btn-border-color: var(--freyja-gold);
  --bs-btn-hover-bg: var(--freyja-navy);
  --bs-btn-hover-color: var(--freyja-offwhite);
  --bs-btn-hover-border-color: var(--freyja-navy);
  --bs-btn-active-bg: var(--freyja-navy);
  --bs-btn-active-color: var(--freyja-offwhite);
  --bs-btn-active-border-color: var(--freyja-navy);
  --bs-btn-focus-shadow-rgb: 201, 160, 118;
  background-color: var(--freyja-gold);
  border-color: var(--freyja-gold);
  color: var(--freyja-navy);
}
.bk-btn.bk-btn-primary:hover,
:host(.solid) .bk-btn.bk-btn-primary:hover {
  background-color: var(--freyja-navy);
  border-color: var(--freyja-navy);
  color: var(--freyja-offwhite);
}
.bk-btn.bk-btn-default,
:host(.solid) .bk-btn.bk-btn-default {
  --bs-btn-bg: var(--freyja-white);
  --bs-btn-color: var(--freyja-navy);
  --bs-btn-border-color: var(--freyja-navy);
  --bs-btn-hover-bg: var(--freyja-navy);
  --bs-btn-hover-color: var(--freyja-offwhite);
  --bs-btn-hover-border-color: var(--freyja-navy);
  --bs-btn-focus-shadow-rgb: 201, 160, 118;
  background-color: var(--freyja-white);
  border: 1px solid var(--freyja-navy);
  color: var(--freyja-navy);
}
.bk-btn.bk-btn-default:hover,
:host(.solid) .bk-btn.bk-btn-default:hover {
  background-color: var(--freyja-navy);
  color: var(--freyja-offwhite);
}
.bk-btn:focus {
  outline: none;
}
.bk-btn:focus-visible {
  outline: 2px solid var(--freyja-gold);
  outline-offset: 2px;
}

/* ---- Inputs ---- */
.bk-input,
.bk-input-group input,
select.bk-input {
  font-family: var(--freyja-font);
  color: var(--freyja-navy);
  background-color: var(--freyja-white);
  border: 1px solid var(--freyja-slate);
  border-radius: var(--freyja-radius);
}
.bk-input:focus,
.bk-input-group input:focus {
  border-color: var(--freyja-navy);
  box-shadow: 0 0 0 2px var(--freyja-gold-20);
  outline: none;
}
label,
.bk-input-group > label {
  font-family: var(--freyja-font);
  font-weight: 500;
  color: var(--freyja-slate-deep);
}

/* ---- Tabs: Navy text, Gold underline on the active tab ----
   Selectors mirror Panel's Bootstrap theme (panel/theme/css/bootstrap.css) so they win on order. */
:host(.bk-above) .bk-header {
  border-bottom: 1px solid var(--freyja-navy-10);
}
:host(.bk-above) .bk-header .bk-tab {
  font-family: var(--freyja-font);
  font-weight: 500;
  color: var(--freyja-slate-deep);
  background: none;
  border: 0;
  border-bottom: 3px solid transparent;
  border-radius: 0;
  padding: 0.55rem 1rem;
}
:host(.bk-above) .bk-header .bk-tab:hover,
.bk-header .bk-tab:focus {
  color: var(--freyja-navy);
  border-color: transparent;
  border-bottom-color: var(--freyja-navy-10);
}
:host(.bk-above) .bk-header .bk-tab.bk-active {
  color: var(--freyja-navy);
  font-weight: 600;
  background: none;
  border-color: transparent;
  border-bottom: 3px solid var(--freyja-gold);
}

/* ---- Alerts (pn.pane.Alert): status colour as a left rule, Navy text ---- */
:host(.alert) {
  font-family: var(--freyja-font);
  color: var(--freyja-navy);
  border: 0;
  border-left: 4px solid var(--freyja-slate);
  border-radius: 0 var(--freyja-radius) var(--freyja-radius) 0;
  padding: 0.6rem 1rem;
}
:host(.alert-warning) {
  color: var(--freyja-navy);
  background-color: var(--freyja-cream);
  border-left-color: var(--freyja-gold);
}
:host(.alert-success) {
  color: var(--freyja-navy);
  background-color: var(--freyja-white);
  border-left-color: var(--freyja-green);
}
:host(.alert-danger) {
  color: var(--freyja-navy);
  background-color: var(--freyja-white);
  border-left-color: var(--freyja-red);
}
:host(.alert-info),
:host(.alert-primary),
:host(.alert-secondary),
:host(.alert-light),
:host(.alert-dark) {
  color: var(--freyja-navy);
  background-color: var(--freyja-lightblue-20);
  border-left-color: var(--freyja-lightblue);
}

/* ---- Tabulator tables: Navy header, White/Cream banding, hairline rules ----
   Selectors mirror Panel's Bootstrap theme so they win on order. */
.tabulator {
  font-family: var(--freyja-font);
  font-size: 0.85rem;
  color: var(--freyja-navy);
  background-color: var(--freyja-white);
  border: 0;
}
.tabulator .tabulator-header,
.tabulator .tabulator-header .tabulator-header-contents,
div .tabulator .tabulator-headers,
div .tabulator .tabulator-header .tabulator-col,
.pnx-tabulator.tabulator .tabulator-header .tabulator-col.tabulator-sortable:hover {
  background-color: var(--freyja-navy);
  color: var(--freyja-offwhite);
  border-color: var(--freyja-navy);
}
.tabulator .tabulator-header .tabulator-col .tabulator-col-title {
  font-weight: 700;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.tabulator .tabulator-header .tabulator-col .tabulator-col-content .tabulator-col-sorter .tabulator-arrow {
  border-bottom-color: var(--freyja-slate);
}
.pnx-tabulator.tabulator .tabulator-tableholder .tabulator-table .tabulator-row {
  background-color: var(--freyja-white);
  color: var(--freyja-navy);
  border-bottom: 1px solid var(--freyja-navy-10);
}
.pnx-tabulator.tabulator .tabulator-tableholder .tabulator-table .tabulator-row.tabulator-row-even {
  background-color: var(--freyja-cream);
  color: var(--freyja-navy);
}
.pnx-tabulator.tabulator .tabulator-tableholder .tabulator-table .tabulator-row.tabulator-selectable:hover {
  background-color: var(--freyja-gold-20);
  color: var(--freyja-navy);
}
.tabulator-row .tabulator-cell {
  border-right: 0;
  font-variant-numeric: tabular-nums lining-nums;
}
.tabulator .tabulator-tableholder .tabulator-placeholder span {
  color: var(--freyja-slate-deep);
  font-weight: 500;
}

/* ---- Header endorsement and footer (HTML panes from app.theme) ---- */
.freyja-endorse {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  float: right;
  text-decoration: none;
}
.freyja-endorse:hover { text-decoration: none; opacity: 0.9; }
.freyja-endorse__label {
  font: 700 0.62rem/1 var(--freyja-font);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--freyja-lightblue);
}
.freyja-endorse__mark svg {
  display: block;
  height: 14px;
  width: auto;
}
.freyja-footer {
  margin-top: 2.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--freyja-navy-10);
  font: 400 0.75rem/1.5 var(--freyja-font);
  color: var(--freyja-slate-deep);
}
.freyja-footer p { margin: 0 0 0.15rem; }
.freyja-footer a { color: var(--freyja-slate-deep); }
```

### `app/assets/freyja-page.css` (document level, injected through the template's `raw_css`)

```css
/* Freyja Consulting brand - document-level stylesheet (template raw_css).
   Fonts are self-hosted from app/assets/fonts (served at ./assets by
   `panel serve --static-dirs assets=app/assets` and run_app.py). */

@font-face { font-family: "Montserrat"; font-style: normal; font-weight: 400; font-display: swap;
  src: url("assets/fonts/Montserrat-400.woff2") format("woff2"); }
@font-face { font-family: "Montserrat"; font-style: normal; font-weight: 500; font-display: swap;
  src: url("assets/fonts/Montserrat-500.woff2") format("woff2"); }
@font-face { font-family: "Montserrat"; font-style: normal; font-weight: 600; font-display: swap;
  src: url("assets/fonts/Montserrat-600.woff2") format("woff2"); }
@font-face { font-family: "Montserrat"; font-style: normal; font-weight: 700; font-display: swap;
  src: url("assets/fonts/Montserrat-700.woff2") format("woff2"); }

:root {
  --bokeh-base-font: "Montserrat", Arial, sans-serif;
  --bs-body-font-family: "Montserrat", Arial, sans-serif;
}

body {
  font-family: "Montserrat", Arial, sans-serif;
  background-color: #FAF9F9;
  color: #0A2E50;
}

/* Header: flat Navy bar with a Gold rule; no drop shadow */
#header {
  box-shadow: none !important;
  border-bottom: 3px solid #C9A076;
}
#header .title,
#header .app-header a.title {
  font-family: "Montserrat", Arial, sans-serif;
  font-weight: 600;
  color: #FAF9F9;
  letter-spacing: 0.01em;
}
#header-items {
  flex: 1 1 auto;
  justify-content: flex-end;
}
```

### Changes to existing files (against `a458cf3`)

```diff
diff --git a/.gitignore b/.gitignore
index 1644795..f565c59 100644
--- a/.gitignore
+++ b/.gitignore
@@ -24,3 +24,4 @@ src/pyre/models/Exposure/__pycache__/exposure_curve_functions.cpython-313.pyc
 src/pyre/models/Exposure/__pycache__/exposure_rating_cost.cpython-313.pyc
 app/__pycache__/*
 app/pages/__pycache__/*
+.cache/montserrat/
diff --git a/app/main.py b/app/main.py
index 036a092..99cb6bd 100644
--- a/app/main.py
+++ b/app/main.py
@@ -15,6 +15,7 @@ from app.pages.contract_config import build_contract_config_page
 from app.pages.data_loading import build_data_loading_page
 from app.pages.results import build_results_page
 from app.state import WorkbenchState
+from app.theme import branded_template
 
 pn.extension("tabulator")
 
@@ -28,9 +29,7 @@ def build_app() -> pn.template.BootstrapTemplate:
         ("3. Run pricing", build_results_page(state)),
     )
 
-    template = pn.template.BootstrapTemplate(title="pyRE Treaty Pricing Workbench")
-    template.main.append(tabs)
-    return template
+    return branded_template(tabs)
 
 
 build_app().servable()
diff --git a/app/pages/contract_config.py b/app/pages/contract_config.py
index a9eaa15..e82ff69 100644
--- a/app/pages/contract_config.py
+++ b/app/pages/contract_config.py
@@ -6,6 +6,7 @@ from datetime import date
 
 import pandas as pd
 import panel as pn
+from bokeh.models.widgets.tables import NumberFormatter
 
 from app.service import build_contract_metadata, build_layer
 from app.state import WorkbenchState
@@ -21,6 +22,26 @@ SELECTABLE_LAYER_TYPES = [
     ContractType.QUOTA_SHARE,
 ]
 
+LAYER_TITLES = {
+    "layer_id": "Layer ID",
+    "layer_name": "Layer",
+    "layer_type": "Type",
+    "occurrence_attachment": "Attachment",
+    "occurrence_limit": "Limit",
+    "full_subject_premium": "Subject premium",
+    "written_line": "Written line",
+    "signed_line": "Signed line",
+}
+_AMOUNT = NumberFormatter(format="0,0", text_align="right")
+_LINE = NumberFormatter(format="0.0%", text_align="right")
+LAYER_FORMATTERS = {
+    "occurrence_attachment": _AMOUNT,
+    "occurrence_limit": _AMOUNT,
+    "full_subject_premium": _AMOUNT,
+    "written_line": _LINE,
+    "signed_line": _LINE,
+}
+
 LAYER_COLUMNS = [
     "layer_id",
     "layer_name",
@@ -59,6 +80,8 @@ def build_contract_config_page(state: WorkbenchState) -> pn.Column:
         show_index=False,
         disabled=True,
         name="Layers",
+        titles=LAYER_TITLES,
+        formatters=LAYER_FORMATTERS,
     )
 
     layer_id = pn.widgets.IntInput(name="Layer ID", value=1)
@@ -74,7 +97,7 @@ def build_contract_config_page(state: WorkbenchState) -> pn.Column:
     written_line = pn.widgets.FloatInput(name="Written line", value=1.0)
     signed_line = pn.widgets.FloatInput(name="Signed line", value=1.0)
 
-    add_layer_button = pn.widgets.Button(name="Add layer", button_type="primary")
+    add_layer_button = pn.widgets.Button(name="Add layer", button_type="default")
     save_contract_button = pn.widgets.Button(name="Save contract metadata", button_type="primary")
 
     def _on_add_layer(_event):
diff --git a/app/pages/results.py b/app/pages/results.py
index ddf4eba..ffafc44 100644
--- a/app/pages/results.py
+++ b/app/pages/results.py
@@ -4,18 +4,47 @@ from __future__ import annotations
 
 import pandas as pd
 import panel as pn
+from bokeh.models.widgets.tables import NumberFormatter
 
 from app.service import run_pricing
 from app.state import WorkbenchState
 
+AMOUNT = NumberFormatter(format="0,0", text_align="right")
+TITLES = {
+    "layer_id": "Layer ID",
+    "layer_name": "Layer",
+    "modelling_year": "Modelling year",
+    "ceded_paid": "Ceded paid",
+    "ceded_incurred": "Ceded incurred",
+    "claim_count": "Claims",
+    "earned_premium": "Earned premium",
+    "loss_ratio": "Loss ratio",
+    "written": "Written",
+    "earned": "Earned",
+}
+FORMATTERS = {
+    "modelling_year": NumberFormatter(format="0"),
+    "ceded_paid": AMOUNT,
+    "ceded_incurred": AMOUNT,
+    "claim_count": NumberFormatter(format="0", text_align="right"),
+    "earned_premium": AMOUNT,
+    "loss_ratio": NumberFormatter(format="0.0%", text_align="right"),
+    "written": AMOUNT,
+    "earned": AMOUNT,
+}
+
 
 def build_results_page(state: WorkbenchState) -> pn.Column:
     status = pn.pane.Alert(
         "Load data and configure a contract, then run pricing.", alert_type="warning"
     )
     run_button = pn.widgets.Button(name="Run pricing", button_type="primary")
-    results_table = pn.widgets.Tabulator(pd.DataFrame(), show_index=False)
-    exposures_table = pn.widgets.Tabulator(pd.DataFrame(), show_index=False)
+    results_table = pn.widgets.Tabulator(
+        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
+    )
+    exposures_table = pn.widgets.Tabulator(
+        pd.DataFrame(), show_index=False, disabled=True, titles=TITLES, formatters=FORMATTERS
+    )
 
     def _on_run(_event):
         if not state.is_ready_to_price():
diff --git a/pyproject.toml b/pyproject.toml
index 719c93d..1b9fbd6 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -97,8 +97,20 @@ dependencies = [
   "panel>=1.4",
   "pandas>=2.0",
 ]
+[tool.hatch.envs.panel.env-vars]
+PYTHONPATH = "."
 [tool.hatch.envs.panel.scripts]
-serve = "panel serve app/main.py --show --autoreload"
+serve = "panel serve app/main.py --static-dirs assets=app/assets --show --autoreload"
+
+[tool.hatch.envs.brand]
+detached = true
+dependencies = [
+  "fonttools>=4.47",
+  "brotli",
+  "uharfbuzz>=0.39",
+]
+[tool.hatch.envs.brand.scripts]
+build = "python scripts/build_brand_assets.py"
 
 [tool.hatch.envs.docs]
 dependencies = [
diff --git a/run_app.py b/run_app.py
index 86953aa..d797f2b 100644
--- a/run_app.py
+++ b/run_app.py
@@ -5,6 +5,7 @@ Usage: python run_app.py
 import panel as pn
 
 from app.main import build_app
+from app.theme import ASSETS_DIR
 
 if __name__ == "__main__":
-    pn.serve(build_app, show=True, autoreload=True)
+    pn.serve(build_app, show=True, autoreload=True, static_dirs={"assets": str(ASSETS_DIR)})
```
