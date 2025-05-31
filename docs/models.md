# Models Module

The Models module provides a variety of actuarial and statistical modeling tools for reinsurance pricing. It includes submodules for experience rating, exposure rating, and aggregate features modeling.

## Submodules

### Experience Rating

The Experience module provides tools for analyzing historical claims experience:

- `burn_cost`: Methods for burn cost analysis
- `curve_fitting`: Functions for fitting curves to data
- `frequency_severity`: Tools for frequency-severity modeling
- `pareto_rating`: Pareto distribution-based rating methods
- `resampling`: Methods for resampling claims data

### Exposure Rating

The Exposure module provides tools for exposure-based rating:

- `mbbefd`: Implementation of the Modified Beta Beta Equivalent Finite Difference (MBBEFD) distribution
- `mixed_exponential`: Implementation of the Mixed Exponential distribution
- `pareto_ilf`: Pareto distribution-based Increased Limit Factors
- `riebesell`: Implementation of the Riebesell approximation

### Aggregate Features

The AggregateFeatures module provides tools for modeling aggregate loss distributions:

- `aggregate_features`: Methods for calculating aggregate loss statistics
- `selections`: Tools for selecting and combining models
- `simulation_engine`: Monte Carlo simulation engine for aggregate losses

### Trending

The trending module provides tools for trending historical data to current levels.

## Examples

### Experience Rating

#### Burn Cost Analysis

```python
from pyre.Models.Experience.burn_cost import BurnCostModel
from pyre.claims.claims import Claims
import numpy as np

# Assuming we have a Claims collection called 'claims_data'

# Create a burn cost model
model = BurnCostModel(claims_data)

# Calculate basic burn cost statistics
burn_cost = model.calculate_burn_cost()
print(f"Average burn cost: {burn_cost}")

# Calculate burn cost with trend
trend_factor = 1.05  # 5% annual trend
years_of_trend = 2
trended_burn_cost = model.calculate_trended_burn_cost(trend_factor, years_of_trend)
print(f"Trended burn cost: {trended_burn_cost}")

# Calculate burn cost with limits
attachment = 1000000
limit = 5000000
limited_burn_cost = model.calculate_limited_burn_cost(attachment, limit)
print(f"Limited burn cost: {limited_burn_cost}")

# Calculate confidence intervals
confidence_level = 0.95
lower, upper = model.calculate_confidence_interval(confidence_level)
print(f"{confidence_level*100}% confidence interval: ({lower}, {upper})")
```

#### Frequency-Severity Modeling

```python
from pyre.Models.Experience.frequency_severity import FrequencySeverityModel
from pyre.claims.claims import Claims
import numpy as np
import matplotlib.pyplot as plt

# Assuming we have a Claims collection called 'claims_data'

# Create a frequency-severity model
model = FrequencySeverityModel(claims_data)

# Fit frequency distribution (Poisson)
freq_params = model.fit_frequency_distribution("poisson")
print(f"Frequency distribution parameters: {freq_params}")

# Fit severity distribution (Lognormal)
sev_params = model.fit_severity_distribution("lognormal")
print(f"Severity distribution parameters: {sev_params}")

# Simulate aggregate losses
num_simulations = 10000
aggregate_losses = model.simulate_aggregate_losses(num_simulations)

# Calculate statistics
mean_loss = np.mean(aggregate_losses)
median_loss = np.median(aggregate_losses)
var_95 = np.percentile(aggregate_losses, 95)
var_99 = np.percentile(aggregate_losses, 99)

print(f"Mean aggregate loss: {mean_loss}")
print(f"Median aggregate loss: {median_loss}")
print(f"95% VaR: {var_95}")
print(f"99% VaR: {var_99}")

# Plot histogram of aggregate losses
plt.figure(figsize=(10, 6))
plt.hist(aggregate_losses, bins=50, alpha=0.7)
plt.axvline(mean_loss, color='r', linestyle='--', label=f'Mean: {mean_loss:.2f}')
plt.axvline(var_95, color='g', linestyle='--', label=f'95% VaR: {var_95:.2f}')
plt.axvline(var_99, color='b', linestyle='--', label=f'99% VaR: {var_99:.2f}')
plt.legend()
plt.title('Simulated Aggregate Loss Distribution')
plt.xlabel('Aggregate Loss')
plt.ylabel('Frequency')
plt.show()
```

### Exposure Rating

#### Increased Limit Factors

```python
from pyre.Models.Exposure.pareto_ilf import ParetoILF
import numpy as np
import matplotlib.pyplot as plt

# Create a Pareto ILF model
alpha = 2.0  # Pareto shape parameter
model = ParetoILF(alpha)

# Calculate increased limit factors
base_limit = 1000000
limits = [1000000, 2000000, 5000000, 10000000, 25000000]
ilfs = [model.calculate_ilf(base_limit, limit) for limit in limits]

print("Increased Limit Factors:")
for limit, ilf in zip(limits, ilfs):
    print(f"  {limit/1000000}M: {ilf:.4f}")

# Calculate layer costs
attachment = 5000000
limit = 5000000
layer_cost = model.calculate_layer_cost(attachment, attachment + limit)
print(f"Layer cost for {attachment/1000000}M xs {limit/1000000}M: {layer_cost:.4f}")

# Plot ILF curve
limits_plot = np.linspace(base_limit, 25000000, 100)
ilfs_plot = [model.calculate_ilf(base_limit, limit) for limit in limits_plot]

plt.figure(figsize=(10, 6))
plt.plot(limits_plot/1000000, ilfs_plot)
plt.scatter([l/1000000 for l in limits], ilfs, color='red', s=50)
plt.title('Pareto Increased Limit Factors')
plt.xlabel('Limit (Millions)')
plt.ylabel('ILF')
plt.grid(True)
plt.show()
```

### Trending

```python
from pyre.Models.trending import apply_trend, compound_trend
import numpy as np
import pandas as pd

# Create sample data
years = [2018, 2019, 2020, 2021, 2022]
values = [100, 110, 125, 135, 150]

# Apply trend to project future values
annual_trend = 0.08  # 8% annual trend
projected_years = [2023, 2024, 2025]
projected_values = apply_trend(values[-1], annual_trend, len(projected_years))

all_years = years + projected_years
all_values = values + projected_values

print("Historical and Projected Values:")
for year, value in zip(all_years, all_values):
    print(f"  {year}: {value:.2f}")

# Calculate compound trend between two periods
start_value = values[0]
end_value = values[-1]
num_periods = len(years) - 1
implied_trend = compound_trend(start_value, end_value, num_periods)
print(f"Implied annual trend: {implied_trend:.2%}")

# Create a DataFrame for analysis
df = pd.DataFrame({
    'Year': all_years,
    'Value': all_values
})

# Calculate year-over-year trends
df['YoY_Trend'] = df['Value'].pct_change()

print("\nYear-over-Year Trends:")
print(df[['Year', 'Value', 'YoY_Trend']])
```

## API Reference

::: pyre.Models.Experience.burn_cost

::: pyre.Models.Experience.curve_fitting

::: pyre.Models.Experience.frequency_severity

::: pyre.Models.Experience.pareto_rating

::: pyre.Models.Experience.resampling

::: pyre.Models.Exposure.mbbefd

::: pyre.Models.Exposure.mixed_exponential

::: pyre.Models.Exposure.pareto_ilf

::: pyre.Models.Exposure.riebesell

::: pyre.Models.AggregateFeatures.aggregate_features

::: pyre.Models.AggregateFeatures.selections

::: pyre.Models.AggregateFeatures.simulation_engine

::: pyre.Models.trending