# Exposures Module

The Exposures module provides tools for managing and analyzing exposure data in reinsurance contexts. It includes classes for representing individual exposures, collections of exposures, and methods for calculating earned and written exposure values.

## Core Classes

### Exposures Data Structure

The module provides a hierarchical structure for representing exposures:

- `ExposureBasis`: An enumeration defining different exposure bases (Earned, Written, etc.)
- `ExposureMetaData`: Contains metadata about an exposure (ID, name, dates, currency, etc.)
- `ExposureValues`: Contains financial values related to exposures (value, attachment point, limit)
- `Exposure`: Combines metadata and values for a single exposure
- `Exposures`: A collection of Exposure objects with methods to access and manipulate them

## Examples

### Creating and Working with Exposures

```python
from pyre.exposures.exposures import Exposure, Exposures, ExposureMetaData, ExposureValues, ExposureBasis
from datetime import date

# Create exposure metadata
metadata = ExposureMetaData(
    exposure_id="EXP001",
    exposure_name="Property Portfolio A",
    exposure_period_start=date(2022, 1, 1),
    exposure_period_end=date(2022, 12, 31),
    currency="USD",
    aggregate=False,
    line_of_business="Property",
    exposure_type=ExposureBasis.EARNED,
    location="US East Coast",
    peril="Hurricane"
)

# Create exposure values
values = ExposureValues(
    exposure_value=10000000,
    attachment_point=1000000,
    limit=5000000
)

# Create an exposure
exposure = Exposure(metadata, values)

# Access exposure properties
print(f"Exposure ID: {exposure.exposure_meta.exposure_id}")
print(f"Exposure Name: {exposure.exposure_meta.exposure_name}")
print(f"Exposure Value: {exposure.exposure_values.exposure_value}")
print(f"Term Length (days): {exposure.exposure_meta.exposure_term_length_days()}")

# Calculate earned exposure as of a specific date
analysis_date = date(2022, 6, 30)  # Mid-year
earned_value = exposure.earned_exposure_value(analysis_date)
print(f"Earned exposure as of {analysis_date}: {earned_value}")

# Calculate written exposure
written_value = exposure.written_exposure_value(analysis_date)
print(f"Written exposure as of {analysis_date}: {written_value}")

# Create a collection of exposures
exposures_collection = Exposures([exposure])

# Add another exposure
second_exposure = Exposure(
    ExposureMetaData(
        "EXP002", 
        "Property Portfolio B",
        date(2022, 4, 1),
        date(2023, 3, 31),
        "EUR",
        exposure_type=ExposureBasis.WRITTEN
    ),
    ExposureValues(5000000, 500000, 2000000)
)
exposures_collection.append(second_exposure)

# Access exposures in the collection
for exp in exposures_collection:
    print(f"Exposure {exp.exposure_meta.exposure_id} - "
          f"Period: {exp.exposure_meta.exposure_period_start} to {exp.exposure_meta.exposure_period_end}")

# Get unique modelling years
print(f"Modelling years: {exposures_collection.modelling_years()}")
```

### Working with Multiple Exposures

```python
from pyre.exposures.exposures import Exposures
import pandas as pd
from datetime import date

# Assuming we have an Exposures collection called 'exposures_data'

# Calculate total earned exposure as of a specific date
analysis_date = date(2022, 12, 31)
total_earned = sum(exp.earned_exposure_value(analysis_date) for exp in exposures_data)
print(f"Total earned exposure as of {analysis_date}: {total_earned}")

# Group exposures by line of business
lob_exposures = {}
for exp in exposures_data:
    lob = exp.exposure_meta.line_of_business
    if lob not in lob_exposures:
        lob_exposures[lob] = []
    lob_exposures[lob].append(exp)

# Calculate earned exposure by line of business
for lob, exps in lob_exposures.items():
    lob_earned = sum(exp.earned_exposure_value(analysis_date) for exp in exps)
    print(f"Earned exposure for {lob}: {lob_earned}")

# Convert exposures to a pandas DataFrame for analysis
exposure_data = []
for exp in exposures_data:
    exposure_data.append({
        'id': exp.exposure_meta.exposure_id,
        'name': exp.exposure_meta.exposure_name,
        'lob': exp.exposure_meta.line_of_business,
        'start_date': exp.exposure_meta.exposure_period_start,
        'end_date': exp.exposure_meta.exposure_period_end,
        'value': exp.exposure_values.exposure_value,
        'earned_value': exp.earned_exposure_value(analysis_date)
    })

df = pd.DataFrame(exposure_data)
print(df.head())

# Analyze exposures by various dimensions
print(f"Total exposure by LOB:\n{df.groupby('lob')['value'].sum()}")
print(f"Average exposure by LOB:\n{df.groupby('lob')['value'].mean()}")
```

## API Reference

::: pyre.exposures.exposures
