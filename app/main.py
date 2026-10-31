"""Panel entrypoint for the pyre treaty pricing workbench.

Run with:  panel serve app/main.py --show --autoreload
(or:       hatch run panel:serve)

Note: this entrypoint must not be named app.py -- Bokeh's script loader
registers the running script under a module name derived from its filename
("app"), which would collide with and shadow the `app` package itself,
breaking `from app.pages import ...` et al.
"""

import panel as pn

from app.pages.contract_config import build_contract_config_page
from app.pages.data_loading import build_data_loading_page
from app.pages.results import build_results_page
from app.state import WorkbenchState

pn.extension("tabulator")


def build_app() -> pn.template.BootstrapTemplate:
    state = WorkbenchState()

    tabs = pn.Tabs(
        ("1. Load data", build_data_loading_page(state)),
        ("2. Configure contract", build_contract_config_page(state)),
        ("3. Run pricing", build_results_page(state)),
    )

    template = pn.template.BootstrapTemplate(title="pyRE Treaty Pricing Workbench")
    template.main.append(tabs)
    return template


build_app().servable()
