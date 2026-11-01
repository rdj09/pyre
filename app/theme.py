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
