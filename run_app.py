"""Convenience launcher for the pyre Shiny web application.

Run from repo root:
    uv run python run_app.py

Equivalent to:
    uv run python -m shiny run app.app

Do NOT run as `shiny run app/app.py` — the file-path form sets __main__
and breaks the relative imports inside app/.
"""

from __future__ import annotations

import shiny


def main() -> None:
    shiny.run_app(
        "app.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
