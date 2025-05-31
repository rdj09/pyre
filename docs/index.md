# pyRE - Python Reinsurance

## Overview
`pyre` is a comprehensive Python package designed to provide pricing tools and utilities for non-life reinsurance professionals. It offers a wide range of actuarial and statistical methods for analyzing claims data, managing exposures, and pricing reinsurance contracts.

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

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description of your changes.

## License
`pyre` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
