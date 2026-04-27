# app/server.py
"""Shiny reactive server — delegates to feature modules via shared reactive state."""
from __future__ import annotations

from shiny import Inputs, Outputs, Session, reactive

from pyre.claims.claims import Claims
from pyre.claims.triangles import Triangle
from pyre.exposures.exposures import Exposures
from pyre.treaty.contracts import RIContract

from .features.contract_module import contract_server
from .features.data_loader_module import data_loader_server
from .features.experience_module import experience_server
from .features.exposure_module import exposure_server
from .features.rate_module import rate_server
from .features.simulation_module import simulation_server
from .features.triangle_module import triangle_server


def server(input: Inputs, output: Outputs, session: Session) -> None:
    _claims: reactive.Value[Claims | None] = reactive.Value(None)
    _exposures: reactive.Value[Exposures | None] = reactive.Value(None)
    _triangle: reactive.Value[Triangle | None] = reactive.Value(None)
    _contract: reactive.Value[RIContract | None] = reactive.Value(None)

    data_loader_server(input, output, session, _claims, _exposures, _triangle)
    triangle_server(input, output, session, _triangle)
    contract_server(input, output, session, _contract)
    experience_server(input, output, session, _claims, _exposures, _contract)
    exposure_server(input, output, session, _exposures, _contract)
    rate_server(input, output, session)
    simulation_server(input, output, session, _claims, _exposures, _contract, _triangle)
