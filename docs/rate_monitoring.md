# Rate Monitoring Module

The Rate Monitoring module provides tools for tracking and analyzing rate changes and rate adequacy over time. It includes methods for calculating rate change indices and assessing rate adequacy.

## Core Components

### Rate Change

The rate_change module provides tools for tracking and analyzing rate changes:

- Functions for calculating rate change indices
- Methods for analyzing the impact of rate changes on a portfolio
- Tools for visualizing rate change trends

### Rate Adequacy

The rate_adequacy module provides tools for assessing the adequacy of rates:

- Methods for comparing actual vs. expected loss ratios
- Tools for analyzing rate adequacy by segment
- Functions for projecting future rate adequacy

## Examples

### Tracking Rate Changes

```python
from pyre.rate_monitoring.rate_change import calculate_rate_change_index
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

# Create sample data
data = {
    'policy_id': ['P001', 'P002', 'P003', 'P004', 'P005'],
    'effective_date': [date(2022, 1, 1), date(2022, 3, 15), date(2022, 6, 1), 
                       date(2022, 9, 10), date(2022, 11, 20)],
    'expiration_date': [date(2023, 1, 1), date(2023, 3, 15), date(2023, 6, 1), 
                        date(2023, 9, 10), date(2023, 11, 20)],
    'premium': [10000, 15000, 8000, 12000, 9000],
    'rate_change_pct': [0.05, 0.03, 0.07, 0.04, 0.06]  # Rate changes at renewal
}

df = pd.DataFrame(data)

# Calculate rate change index
base_date = date(2022, 1, 1)
evaluation_dates = [date(2022, 3, 31), date(2022, 6, 30), 
                   date(2022, 9, 30), date(2022, 12, 31)]

indices = []
for eval_date in evaluation_dates:
    index = calculate_rate_change_index(df, base_date, eval_date)
    indices.append(index)
    print(f"Rate change index as of {eval_date}: {index:.4f}")

# Plot rate change index over time
plt.figure(figsize=(10, 6))
plt.plot([d.strftime('%Y-%m-%d') for d in evaluation_dates], indices, marker='o')
plt.title('Rate Change Index Over Time')
plt.xlabel('Evaluation Date')
plt.ylabel('Rate Change Index')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Calculate cumulative rate change
cumulative_change = (indices[-1] - 1.0) * 100
print(f"Cumulative rate change from {base_date} to {evaluation_dates[-1]}: {cumulative_change:.2f}%")

# Calculate annualized rate change
days_elapsed = (evaluation_dates[-1] - base_date).days
years_elapsed = days_elapsed / 365.25
annualized_change = ((indices[-1]) ** (1/years_elapsed) - 1) * 100
print(f"Annualized rate change: {annualized_change:.2f}%")
```

### Analyzing Rate Adequacy

```python
from pyre.rate_monitoring.rate_adequacy import calculate_rate_adequacy
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample data
np.random.seed(42)
n_policies = 100

data = {
    'policy_id': [f'P{i:03d}' for i in range(1, n_policies + 1)],
    'line_of_business': np.random.choice(['Property', 'Casualty', 'Marine'], n_policies),
    'premium': np.random.uniform(5000, 50000, n_policies),
    'incurred_losses': np.random.uniform(2000, 40000, n_policies),
    'expected_loss_ratio': np.random.uniform(0.5, 0.7, n_policies)
}

df = pd.DataFrame(data)

# Calculate rate adequacy
df['actual_loss_ratio'] = df['incurred_losses'] / df['premium']
df['rate_adequacy'] = calculate_rate_adequacy(df['actual_loss_ratio'], df['expected_loss_ratio'])

# Print summary statistics
print("Rate Adequacy Summary:")
print(f"Average Rate Adequacy: {df['rate_adequacy'].mean():.2%}")
print(f"Median Rate Adequacy: {df['rate_adequacy'].median():.2%}")
print(f"Min Rate Adequacy: {df['rate_adequacy'].min():.2%}")
print(f"Max Rate Adequacy: {df['rate_adequacy'].max():.2%}")

# Analyze rate adequacy by line of business
lob_summary = df.groupby('line_of_business').agg({
    'premium': 'sum',
    'incurred_losses': 'sum',
    'rate_adequacy': 'mean'
}).reset_index()

lob_summary['actual_loss_ratio'] = lob_summary['incurred_losses'] / lob_summary['premium']

print("\nRate Adequacy by Line of Business:")
for _, row in lob_summary.iterrows():
    print(f"{row['line_of_business']}:")
    print(f"  Premium: ${row['premium']:.2f}")
    print(f"  Incurred Losses: ${row['incurred_losses']:.2f}")
    print(f"  Actual Loss Ratio: {row['actual_loss_ratio']:.2%}")
    print(f"  Average Rate Adequacy: {row['rate_adequacy']:.2%}")

# Visualize rate adequacy distribution
plt.figure(figsize=(12, 8))

# Histogram of rate adequacy
plt.subplot(2, 2, 1)
plt.hist(df['rate_adequacy'], bins=20, alpha=0.7)
plt.axvline(0, color='r', linestyle='--')
plt.title('Distribution of Rate Adequacy')
plt.xlabel('Rate Adequacy')
plt.ylabel('Frequency')

# Rate adequacy by line of business
plt.subplot(2, 2, 2)
bars = plt.bar(lob_summary['line_of_business'], lob_summary['rate_adequacy'])
for i, bar in enumerate(bars):
    if lob_summary['rate_adequacy'].iloc[i] < 0:
        bar.set_color('red')
    else:
        bar.set_color('green')
plt.axhline(0, color='black', linestyle='-')
plt.title('Average Rate Adequacy by Line of Business')
plt.ylabel('Rate Adequacy')

# Scatter plot of premium vs. rate adequacy
plt.subplot(2, 2, 3)
for lob in df['line_of_business'].unique():
    subset = df[df['line_of_business'] == lob]
    plt.scatter(subset['premium'], subset['rate_adequacy'], alpha=0.7, label=lob)
plt.axhline(0, color='r', linestyle='--')
plt.title('Premium vs. Rate Adequacy')
plt.xlabel('Premium')
plt.ylabel('Rate Adequacy')
plt.legend()

# Actual vs. Expected Loss Ratio
plt.subplot(2, 2, 4)
plt.scatter(df['expected_loss_ratio'], df['actual_loss_ratio'], alpha=0.5)
plt.plot([0.4, 0.8], [0.4, 0.8], 'r--')  # Diagonal line
plt.title('Actual vs. Expected Loss Ratio')
plt.xlabel('Expected Loss Ratio')
plt.ylabel('Actual Loss Ratio')

plt.tight_layout()
plt.show()
```

## API Reference

::: pyre.rate_monitoring.rate_change

::: pyre.rate_monitoring.rate_adequacy