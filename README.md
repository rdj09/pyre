# pyRE - Python Reinsurance

|   |  |
| --- | --- |
| Docs | [![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://rdj09.github.io/pyre/) |
| Meta | [![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch) [![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/) [![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![Version](https://img.shields.io/badge/version-0.0.1-green.svg)]() |

## Overview

`pyre` is a comprehensive Python package designed to provide pricing tools and utilities for non-life reinsurance professionals. It offers a wide range of actuarial and statistical methods for analyzing claims data, managing exposures, and pricing reinsurance contracts.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Directory Structure](#directory-structure)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Claims Analysis**: Tools for managing and analyzing claims data, including development triangles and IBNER pattern extraction
- **Exposure Management**: Classes for handling exposure data with various bases (earned, written)
- **Treaty Modeling**: Functionality for modeling reinsurance contracts and layers
- **Experience Rating**: Methods for burn cost analysis, frequency-severity modeling, and curve fitting
- **Rate Monitoring**: Tools for tracking rate adequacy and rate changes

## Installation

To install the package, clone the repository and install the dependencies:

```bash
git clone https://github.com/rdj09/pyre.git
cd pyre
pip install -e .
```

## Quick Start

Here's a simple example of how to use the package to analyze claims data:

```python
# Import the claims module
from pyre.claims.claims import Claim, Claims, ClaimsMetaData, ClaimDevelopmentHistory
from pyre.claims.triangles import Triangle
from datetime import date

# Create a claim with metadata and development history
metadata = ClaimsMetaData(
    claim_id="CL001",
    currency="USD",
    loss_date=date(2022, 1, 15),
    report_date=date(2022, 2, 1),
    line_of_business="Property"
)

development = ClaimDevelopmentHistory(
    development_months=[0, 3, 6, 9, 12],
    cumulative_dev_paid=[0, 10000, 25000, 40000, 50000],
    cumulative_dev_incurred=[100000, 90000, 75000, 60000, 50000]
)

claim = Claim(metadata, development)

# Create a collection of claims
claims_collection = Claims([claim])

# Create a triangle from claims data
triangle = Triangle.from_claims(claims_collection, value_type="incurred")

# Calculate age-to-age factors
factors = triangle.calculate_age_to_age_factors()
print(factors)
```

## Directory Structure

```
pyre/
├── docs/               # Documentation
├── src/                # Source code
│   └── pyre/
│       ├── claims/     # Claims analysis tools
│       ├── exposures/  # Exposure management
│       ├── Models/     # Pricing models
│       ├── treaty/     # Reinsurance contract modeling
│       └── rate_monitoring/ # Rate monitoring tools
└── tests/              # Test suite
```

## Documentation

Comprehensive documentation is available at [https://rdj09.github.io/pyre/](https://rdj09.github.io/pyre/).

The documentation includes:
- Detailed API references
- Usage examples
- Tutorials for specific use cases
- Explanations of actuarial concepts and methodologies

To build the documentation locally:

```bash
pip install -e ".[docs]"
hatch run docs:serve
```

Then visit `http://localhost:8000` in your browser.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch for your feature or bug fix
3. Write tests for your changes
4. Ensure all tests pass with `pytest`
5. Submit a pull request with a detailed description of your changes

## License

`pyre` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
