"""Panel entrypoint for the pyre treaty pricing workbench.

Run with:  panel serve app/main.py --show --autoreload
(or:       hatch run panel:serve)

Note: this entrypoint must not be named app.py -- Bokeh's script loader
registers the running script under a module name derived from its filename
("app"), which would collide with and shadow the `app` package itself,
breaking `from app.pages import ...` et al.
"""

import panel as pn

from app.db import DB_PATH, init_db
from app.pages.compare import build_compare_page
from app.pages.contract_config import build_contract_config_page
from app.pages.data_loading import build_data_loading_page
from app.pages.model_library import build_model_library_page
from app.pages.results import build_results_page
from app.state import WorkbenchState
from app.theme import branded_template

pn.extension("tabulator")


def build_app() -> pn.template.BootstrapTemplate:
    state = WorkbenchState()
    init_db(DB_PATH)

    # Forward-reference closures: each of these is only *called* later (after
    # `tabs` exists below), never at definition time, so it's safe for them to
    # reference each other and `tabs` out of definition order.
    def _build_editable_tabs():
        return [
            ("1. Load data", build_data_loading_page(state)),
            ("2. Configure contract", build_contract_config_page(state)),
            ("3. Run pricing", build_results_page(state, on_save=_refresh_catalog_tabs)),
        ]

    def _on_load():
        new_tabs = _build_editable_tabs()
        for i, pair in enumerate(new_tabs):
            tabs[i] = pair

    def _refresh_catalog_tabs():
        # Saving a version (tab 2), or Copying/Deleting one (tab 3 itself),
        # changes the set of saved versions -- rebuild both the Saved Models
        # catalog/picker and the Compare picker so neither keeps showing
        # stale (session-start, or pre-change) options.
        tabs[3] = (
            "4. Saved Models",
            build_model_library_page(state, on_load=_on_load, on_change=_refresh_catalog_tabs),
        )
        tabs[4] = ("5. Compare", build_compare_page(state))

    tabs = pn.Tabs(*_build_editable_tabs())

    tabs.append(
        (
            "4. Saved Models",
            build_model_library_page(state, on_load=_on_load, on_change=_refresh_catalog_tabs),
        )
    )
    tabs.append(("5. Compare", build_compare_page(state)))

    return branded_template(tabs)


build_app().servable()
