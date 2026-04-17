# Simulation (DFA)

The `Simulation` class implements a Monte Carlo DFA (Dynamic Financial Analysis) pricing engine for reinsurance contracts.

## Overview

For each simulation trial:

1. Sample number of claims from a frequency distribution (Poisson or Negative Binomial)
2. Sample individual claim sizes from a severity distribution (Lognormal or Pareto)
3. Apply reinsurance layer terms (per-occurrence limit/attachment, aggregate terms)
4. Apply retrocession (optional)
5. Compute investment return on premium float

After N simulations, compute:

- **Loss cost** — mean ceded loss per layer
- **Required capital** — TVaR(99.5%) at the configured confidence level (Solvency II basis)
- **Required premium** — actuarially fair premium incorporating cost of capital, expenses, investment return

## Basic usage

```python
from datetime import date
from pyre.models.aggregate.simulation_engine import Simulation
from pyre.models.aggregate.aggregate_features import ModellingAssumptions
from pyre.models.experience.frequency_severity import FrequencyFit, SeverityFit
from pyre.enums import FrequencyDistribution, SeverityDistribution

assumptions = ModellingAssumptions(
    cost_of_capital=0.08,
    required_rate_of_return=0.10,
    capital_confidence_level=0.995,
    use_tvar=True,
    investment_yield=0.03,
    acquisition_cost_ratio=0.05,
    brokerage_cost_ratio=0.025,
)

freq_fit = FrequencyFit(
    distributions=[FrequencyDistribution.POISSON],
    data=experience_data,
)
sev_fit = SeverityFit(
    distributions=[SeverityDistribution.LOGNORMAL],
    data=experience_data,
    ibner_dev_pattern={2020: 1.05, 2021: 1.02},
)

sim = Simulation(
    frequency_fit=freq_fit,
    severity_fit=sev_fit,
    ri_contract=contract,
    assumptions=assumptions,
    n_simulations=10_000,
    random_seed=42,
)
sim.run()

print("Loss cost by layer:", sim.loss_cost())
print("Required capital:", sim.required_capital())
print("Required premium:", sim.required_premium_layer())
print("Programme premium:", sim.required_premium_programme())

# Save results to JSON
sim.save("results.json")
```

## ModellingAssumptions fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cost_of_capital` | `float` | required | Required return on risk capital (e.g. 0.08 = 8%) |
| `required_rate_of_return` | `float` | required | Minimum acceptable return on equity |
| `capital_confidence_level` | `float` | `0.995` | VaR/TVaR confidence level (Solvency II = 99.5%) |
| `use_tvar` | `bool` | `True` | If True, use TVaR; if False, use VaR |
| `investment_yield` | `float` | `0.0` | Annual investment return on float |
| `tax_rate` | `float` | `0.0` | Combined premium and profit tax rate |
| `acquisition_cost_ratio` | `float` | `0.0` | Acquisition costs as proportion of premium |
| `brokerage_cost_ratio` | `float` | `0.0` | Brokerage as proportion of premium |

## Required premium formula

```
P = (loss_cost + CoC × required_capital - investment_return + net_retrocession_cost)
    / (1 - acquisition_cost_ratio - brokerage_cost_ratio)
```

where:
- `required_capital` = TVaR or VaR at `capital_confidence_level`
- `investment_return` = signed premium × `investment_yield`
- `net_retrocession_cost` = retrocession premium − retrocession recovery (if configured)

## AggregateFeatures orchestrator

For a full pricing workflow, use `AggregateFeatures`:

```python
from pyre.models.aggregate.aggregate_features import AggregateFeatures, ModellingAssumptions
from pyre.models.aggregate.selections import Selections

assumptions = ModellingAssumptions(cost_of_capital=0.08, required_rate_of_return=0.10)
selections = Selections(experience_data=exp_data, exposure_data=exp_model)

ag = AggregateFeatures(
    experience_data=exp_data,
    exposure_data=exp_model,
    selections=selections,
    assumptions=assumptions,
)
results = ag.run(n_simulations=10_000)
```
