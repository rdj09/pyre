# Claims Module

The Claims module provides tools for managing and analyzing claims data in reinsurance contexts. It includes classes for representing individual claims, collections of claims, and claims development triangles.

## Core Classes

### Claims Data Structure

The module provides a hierarchical structure for representing claims:

- `ClaimYearType`: An enumeration defining different claim year bases (Accident Year, Underwriting Year, etc.)
- `ClaimDevelopmentHistory`: Tracks the development of a claim over time, including paid and incurred amounts
- `ClaimsMetaData`: Contains metadata about a claim (ID, dates, limits, etc.)
- `Claim`: Combines metadata and development history for a single claim
- `Claims`: A collection of Claim objects with methods to access and manipulate them

### Claims Triangles

The triangles module provides tools for creating and analyzing claims development triangles:

- `Triangle`: Represents a claims development triangle with methods for:
  - Converting between cumulative and incremental triangles
  - Calculating age-to-age factors
  - Fitting curves to development patterns
- `IBNERPatternExtractor`: Extracts IBNER (Incurred But Not Enough Reported) patterns from triangles

## Examples

### Creating and Working with Claims

```python
from pyre.claims.claims import Claim, Claims, ClaimsMetaData, ClaimDevelopmentHistory, ClaimYearType
from datetime import date

# Create claim metadata
metadata = ClaimsMetaData(
    claim_id="CL001",
    currency="USD",
    contract_limit=1000000,
    contract_deductible=10000,
    claim_year_basis=ClaimYearType.ACCIDENT_YEAR,
    loss_date=date(2022, 3, 15),
    report_date=date(2022, 4, 1),
    line_of_business="Property"
)

# Create claim development history
development = ClaimDevelopmentHistory(
    development_months=[0, 3, 6, 9, 12],
    cumulative_dev_paid=[0, 15000, 30000, 45000, 50000],
    cumulative_dev_incurred=[80000, 70000, 60000, 55000, 50000]
)

# Create a claim
claim = Claim(metadata, development)

# Access claim properties
print(f"Claim ID: {claim.claims_meta_data.claim_id}")
print(f"Latest paid amount: {claim.uncapped_claim_development_history.latest_paid()}")
print(f"Latest incurred amount: {claim.uncapped_claim_development_history.latest_incurred()}")
print(f"Latest reserved amount: {claim.uncapped_claim_development_history.latest_reserved_amount()}")

# Create a collection of claims
claims_collection = Claims([claim])

# Add another claim
second_claim = Claim(
    ClaimsMetaData("CL002", "EUR", loss_date=date(2022, 5, 10)),
    ClaimDevelopmentHistory(
        [0, 3, 6],
        [0, 5000, 10000],
        [20000, 15000, 12000]
    )
)
claims_collection.append(second_claim)

# Access claims in the collection
for claim in claims_collection:
    print(f"Claim {claim.claims_meta_data.claim_id} - "
          f"Loss date: {claim.claims_meta_data.loss_date}")

# Get unique modelling years
print(f"Modelling years: {claims_collection.modelling_years()}")
```

### Working with Claims Triangles

```python
from pyre.claims.triangles import Triangle, CurveType
from pyre.claims.claims import Claims

# Assuming we have a Claims collection called 'claims_data'

# Create a triangle from claims data
incurred_triangle = Triangle.from_claims(claims_data, value_type="incurred")
paid_triangle = Triangle.from_claims(claims_data, value_type="paid")

# Display the triangle
print(incurred_triangle)

# Convert to incremental triangle
incremental_triangle = incurred_triangle.to_incremental()

# Calculate age-to-age factors
factors = incurred_triangle.calculate_age_to_age_factors()
print("Age-to-age factors:")
for origin_year, factors_dict in factors.items():
    print(f"  Year {origin_year}: {factors_dict}")

# Get average age-to-age factors
avg_factors = incurred_triangle.get_average_age_to_age_factors(method="volume")
print(f"Volume-weighted average factors: {avg_factors}")

# Fit a curve to the development pattern
curve_params = incurred_triangle.fit_curve(CurveType.EXPONENTIAL)
print(f"Curve parameters: {curve_params}")

# Extract IBNER pattern
ibner_extractor = IBNERPatternExtractor(incurred_triangle)
ibner_pattern = ibner_extractor.get_IBNER_pattern()
print(f"IBNER pattern: {ibner_pattern}")
```

## API Reference

::: pyre.claims.claims

::: pyre.claims.triangles
