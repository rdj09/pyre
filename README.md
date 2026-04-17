# pyRE - Python Reinsurance

|   |  |
| --- | --- |
| Docs | [![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rdj09.github.io/pyre/) |
| Meta | [![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) [![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Version](https://img.shields.io/badge/version-1.0.0-green.svg)]() |

## Overview

`pyre` is a comprehensive Python package for non-life reinsurance pricing. It provides actuarial and statistical methods for claims analysis, exposure management, experience rating, and DFA simulation.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Examples](#examples)
- [Development](#development)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Claims Analysis** — Development triangles, IBNER pattern extraction, chain-ladder factors
- **Exposure Management** — Earned/written exposure tracking with parallelogram method
- **Treaty Modelling** — XOL, quota share, franchise, aggregate stop-loss layer terms
- **Experience Rating** — Burn cost (chain-ladder, BF, Cape Cod), frequency/severity fitting
- **Exposure Rating** — MBBEFD, mixed-exponential, and Riebesell curves
- **DFA Simulation** — Monte Carlo pricing engine with TVaR capital, investment return, profit commission, retrocession
- **Rate Monitoring** — Rate change and rate adequacy tracking

## Installation

### With uv (recommended)

```bash
uv pip install pyre
```

Or directly from source:

```bash
git clone https://github.com/rdj09/pyre.git
cd pyre
uv pip install -e .
```

### With pip

```bash
pip install pyre
```

## Quick Start

```python
from datetime import date
from pyre import (
    Claim, ClaimDevelopmentHistory, Claims, ClaimsMetaData,
    ClaimYearType, Triangle, CurveType,
)

# Build a claim
meta = ClaimsMetaData(
    claim_id="CL001", currency="USD",
    loss_date=date(2022, 1, 15), report_date=date(2022, 2, 1),
    line_of_business="Property",
)
dev = ClaimDevelopmentHistory(
    development_months=[12, 24, 36],
    cumulative_dev_paid=[0, 10_000, 25_000],
    cumulative_dev_incurred=[100_000, 80_000, 60_000],
)
claims = Claims([Claim(meta, dev)])

# Build a paid development triangle and fit a curve
triangle = Triangle.from_claims(claims, value_type="paid")
pattern = triangle.get_selected_development_pattern(
    curve_type=CurveType.EXPONENTIAL,
    tail_factor=1.05,
)
print(pattern)  # {12: 4.32, 24: 1.87, 36: 1.05}
```

## Examples

The `examples/` directory contains four runnable scripts:

| Script | Covers |
|--------|--------|
| `examples/01_claims_analysis.py` | Claims, triangles, development curves, IBNER |
| `examples/02_experience_rating.py` | BurnCostModel — chain-ladder, BF, Cape Cod |
| `examples/03_dfa_simulation.py` | Full DFA Monte Carlo pricing with sensitivity analysis |
| `examples/04_exposure_rating.py` | MBBEFD / mixed-exponential exposure rating |

Run any example with:

```bash
uv run python examples/01_claims_analysis.py
```

## Development

### Prerequisites

Install [uv](https://docs.astral.sh/uv/):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Setup

```bash
git clone https://github.com/rdj09/pyre.git
cd pyre

# Install in editable mode with dev dependencies
uv sync
```

### Running tests

```bash
# All tests with coverage
uv run pytest --cov=pyre --cov-report=term-missing --cov-fail-under=80

# Quick (no coverage)
uv run pytest
```

### Linting and formatting

```bash
uv run ruff check src/pyre tests
uv run ruff format src/pyre tests
```

### Type checking

```bash
uv run mypy src/pyre
```

### All checks in one go

```bash
uv run ruff check src/pyre tests && \
uv run ruff format --check src/pyre tests && \
uv run mypy src/pyre && \
uv run pytest --cov=pyre --cov-fail-under=80
```

### Pre-commit hooks

```bash
uv run pre-commit install
```

### Building documentation locally

```bash
uv pip install -e ".[docs]"    # or: uv sync --group docs
uv run mkdocs serve --dev-addr localhost:8000
```

Then visit [http://localhost:8000](http://localhost:8000).

## Directory Structure

```
pyre/
├── examples/           # Runnable usage examples
├── docs/               # MkDocs documentation source
├── src/
│   └── pyre/
│       ├── claims/         # Claims data and development triangles
│       ├── exposures/      # Exposure management
│       ├── models/
│       │   ├── experience/ # Burn cost, freq/sev fitting, resampling
│       │   ├── exposure/   # MBBEFD, mixed-exponential, ILF fitting
│       │   └── aggregate/  # Selections, DFA simulation engine
│       ├── treaty/         # Contract structures and layer functions
│       ├── rate_monitoring/ # Rate change and adequacy
│       └── enums.py        # All cross-cutting enumerations
└── tests/              # pytest test suite (>80% coverage)
```

## Documentation

Full API reference and tutorials: [https://rdj09.github.io/pyre/](https://rdj09.github.io/pyre/)

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on branching, testing, and pull requests.

## License

`pyre` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) licence.
