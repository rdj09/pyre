"""Build the Freyja Consulting brand assets used by the Treaty Pricing Workbench
and the MkDocs documentation site.

Outputs (committed to the repo; rerun only if the brand changes), written
identically under both app/assets/ (Panel app) and docs/assets/ (MkDocs,
which can only serve static files from inside its docs_dir):
  <root>/brand/freyja-wordmark-offwhite.svg   wordmark for the Navy header
  <root>/brand/freyja-wordmark-navy.svg       wordmark for light backgrounds (README, docs)
  <root>/brand/favicon.svg                    browser-tab icon
  <root>/fonts/Montserrat-{400,500,600,700}.woff2   Latin-subset web fonts
  <root>/fonts/OFL.txt                        Montserrat licence (SIL OFL 1.1)

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
DOCS_ASSETS = REPO / "docs" / "assets"
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
    licence = fetch("OFL.txt", args.fonts_dir)

    for root in (ASSETS, DOCS_ASSETS):
        brand = root / "brand"
        brand.mkdir(parents=True, exist_ok=True)
        (brand / "freyja-wordmark-offwhite.svg").write_text(wordmark(fonts, OFFWHITE), encoding="utf-8")
        (brand / "freyja-wordmark-navy.svg").write_text(wordmark(fonts, NAVY), encoding="utf-8")
        (brand / "favicon.svg").write_text(favicon(fonts), encoding="utf-8")
        web_fonts(fonts, root / "fonts")
        (root / "fonts" / "OFL.txt").write_bytes(licence.read_bytes())

    for root in (ASSETS, DOCS_ASSETS):
        for p in sorted(root.rglob("*")):
            if p.is_file():
                print(f"{p.relative_to(REPO)}  {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
