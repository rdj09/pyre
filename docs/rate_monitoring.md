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
from pyre.rate_monitoring.rate_change import rate_change_simple, rate_change_adjusted
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

# Create sample data for policies with renewals
data = {
    'policy_id': ['P001', 'P001', 'P002', 'P002', 'P003', 'P003'],
    'year': [2022, 2023, 2022, 2023, 2022, 2023],
    'expiring_premium': [None, 10000, None, 15000, None, 8000],
    'renewed_premium': [10000, 10500, 15000, 15450, 8000, 8560],
    'exposure_change': [None, 0, None, 0.05, None, 0]  # 5% exposure increase for P002
}

df = pd.DataFrame(data)

# Calculate simple rate changes
rate_changes = []
adjusted_rate_changes = []

for policy in df['policy_id'].unique():
    policy_data = df[df['policy_id'] == policy].sort_values('year')
    if len(policy_data) > 1:
        expiring = policy_data.iloc[0]['renewed_premium']
        renewed = policy_data.iloc[1]['renewed_premium']
        exposure_change = policy_data.iloc[1]['exposure_change']

        # Simple rate change (no adjustment for exposure)
        simple_change = rate_change_simple(expiring, renewed)

        # Adjusted rate change (accounting for exposure changes)
        if exposure_change:
            adjusted_expiring = expiring * (1 + exposure_change)
            adjusted_change = rate_change_adjusted(expiring, renewed, adjusted_expiring)
        else:
            adjusted_change = simple_change

        rate_changes.append({
            'policy_id': policy,
            'expiring_premium': expiring,
            'renewed_premium': renewed,
            'exposure_change': exposure_change,
            'simple_rate_change': simple_change,
            'adjusted_rate_change': adjusted_change
        })

# Convert to DataFrame for analysis
rate_change_df = pd.DataFrame(rate_changes)

# Print rate changes
print("Rate Changes by Policy:")
for _, row in rate_change_df.iterrows():
    print(f"Policy {row['policy_id']}:")
    print(f"  Expiring Premium: ${row['expiring_premium']:.2f}")
    print(f"  Renewed Premium: ${row['renewed_premium']:.2f}")
    print(f"  Exposure Change: {row['exposure_change'] or 0:.1%}")
    print(f"  Simple Rate Change: {row['simple_rate_change']:.2%}")
    print(f"  Adjusted Rate Change: {row['adjusted_rate_change']:.2%}")

# Calculate portfolio averages
avg_simple_change = rate_change_df['simple_rate_change'].mean()
avg_adjusted_change = rate_change_df['adjusted_rate_change'].mean()
weighted_avg_change = (rate_change_df['adjusted_rate_change'] * rate_change_df['expiring_premium']).sum() / rate_change_df['expiring_premium'].sum()

print("\nPortfolio Rate Change Summary:")
print(f"  Simple Average Rate Change: {avg_simple_change:.2%}")
print(f"  Adjusted Average Rate Change: {avg_adjusted_change:.2%}")
print(f"  Premium-Weighted Average Rate Change: {weighted_avg_change:.2%}")

# Visualize rate changes
plt.figure(figsize=(10, 6))
plt.bar(rate_change_df['policy_id'], rate_change_df['simple_rate_change'], alpha=0.7, label='Simple Rate Change')
plt.bar(rate_change_df['policy_id'], rate_change_df['adjusted_rate_change'], alpha=0.7, label='Adjusted Rate Change')
plt.axhline(y=0, color='r', linestyle='-')
plt.axhline(y=weighted_avg_change, color='g', linestyle='--', label='Weighted Average')
plt.title('Rate Changes by Policy')
plt.xlabel('Policy ID')
plt.ylabel('Rate Change')
plt.legend()
plt.grid(True, axis='y')
plt.tight_layout()
plt.show()
```

### Analyzing Rate Adequacy

```python
from pyre.rate_monitoring.rate_adequacy import rate_adequacy, rate_adequacy_change
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample data
np.random.seed(42)
n_policies = 100

# Current period data
current_data = {
    'policy_id': [f'P{i:03d}' for i in range(1, n_policies + 1)],
    'line_of_business': np.random.choice(['Property', 'Casualty', 'Marine'], n_policies),
    'premium': np.random.uniform(5000, 50000, n_policies),
    'incurred_losses': np.random.uniform(2000, 40000, n_policies),
    'indicated_premium': np.random.uniform(4000, 55000, n_policies)
}

# Prior period data (with some rate changes)
prior_data = {
    'policy_id': [f'P{i:03d}' for i in range(1, n_policies + 1)],
    'premium': [p * np.random.uniform(0.9, 1.0) for p in current_data['premium']],
    'incurred_losses': [l * np.random.uniform(0.85, 1.05) for l in current_data['incurred_losses']],
    'indicated_premium': [p * np.random.uniform(0.9, 1.0) for p in current_data['indicated_premium']]
}

# Create DataFrames
current_df = pd.DataFrame(current_data)
prior_df = pd.DataFrame(prior_data)

# Calculate rate adequacy for current period
current_df['adequacy'] = current_df.apply(
    lambda row: rate_adequacy(row['premium'], row['indicated_premium']), 
    axis=1
)

# Calculate rate adequacy for prior period
prior_df['adequacy'] = prior_df.apply(
    lambda row: rate_adequacy(row['premium'], row['indicated_premium']), 
    axis=1
)

# Merge the dataframes to calculate change in adequacy
df = current_df.merge(prior_df, on='policy_id', suffixes=('', '_prior'))
df['adequacy_change'] = df.apply(
    lambda row: rate_adequacy_change(
        row['premium_prior'], row['indicated_premium_prior'],
        row['premium'], row['indicated_premium']
    ),
    axis=1
)

# Calculate actual loss ratios
df['actual_lr'] = df['incurred_losses'] / df['premium']
df['actual_lr_prior'] = df['incurred_losses_prior'] / df['premium_prior']
df['lr_change'] = df['actual_lr'] - df['actual_lr_prior']

# Print summary statistics
print("Rate Adequacy Summary:")
print(f"Average Rate Adequacy (Current): {df['adequacy'].mean():.2%}")
print(f"Average Rate Adequacy (Prior): {df['adequacy_prior'].mean():.2%}")
print(f"Average Change in Adequacy: {df['adequacy_change'].mean():.2%}")
print(f"Median Rate Adequacy (Current): {df['adequacy'].median():.2%}")
print(f"Min Rate Adequacy (Current): {df['adequacy'].min():.2%}")
print(f"Max Rate Adequacy (Current): {df['adequacy'].max():.2%}")

# Analyze rate adequacy by line of business
lob_summary = df.groupby('line_of_business').agg({
    'premium': 'sum',
    'premium_prior': 'sum',
    'incurred_losses': 'sum',
    'incurred_losses_prior': 'sum',
    'adequacy': 'mean',
    'adequacy_prior': 'mean',
    'adequacy_change': 'mean'
}).reset_index()

lob_summary['actual_lr'] = lob_summary['incurred_losses'] / lob_summary['premium']
lob_summary['actual_lr_prior'] = lob_summary['incurred_losses_prior'] / lob_summary['premium_prior']
lob_summary['lr_change'] = lob_summary['actual_lr'] - lob_summary['actual_lr_prior']

print("\nRate Adequacy by Line of Business:")
for _, row in lob_summary.iterrows():
    print(f"{row['line_of_business']}:")
    print(f"  Current Premium: ${row['premium']:.2f}")
    print(f"  Current Loss Ratio: {row['actual_lr']:.2%}")
    print(f"  Current Adequacy: {row['adequacy']:.2%}")
    print(f"  Prior Adequacy: {row['adequacy_prior']:.2%}")
    print(f"  Change in Adequacy: {row['adequacy_change']:.2%}")

# Visualize rate adequacy
plt.figure(figsize=(12, 8))

# Histogram of rate adequacy
plt.subplot(2, 2, 1)
plt.hist(df['adequacy'], bins=20, alpha=0.7, label='Current')
plt.hist(df['adequacy_prior'], bins=20, alpha=0.5, label='Prior')
plt.axvline(1.0, color='r', linestyle='--')
plt.title('Distribution of Rate Adequacy')
plt.xlabel('Rate Adequacy (1.0 = Adequate)')
plt.ylabel('Frequency')
plt.legend()

# Rate adequacy by line of business
plt.subplot(2, 2, 2)
x = np.arange(len(lob_summary))
width = 0.35
plt.bar(x - width/2, lob_summary['adequacy_prior'], width, label='Prior', alpha=0.7)
plt.bar(x + width/2, lob_summary['adequacy'], width, label='Current', alpha=0.7)
plt.axhline(1.0, color='black', linestyle='-')
plt.xticks(x, lob_summary['line_of_business'])
plt.title('Rate Adequacy by Line of Business')
plt.ylabel('Rate Adequacy')
plt.legend()

# Scatter plot of premium vs. rate adequacy
plt.subplot(2, 2, 3)
for lob in df['line_of_business'].unique():
    subset = df[df['line_of_business'] == lob]
    plt.scatter(subset['premium'], subset['adequacy'], alpha=0.7, label=lob)
plt.axhline(1.0, color='r', linestyle='--')
plt.title('Premium vs. Rate Adequacy')
plt.xlabel('Premium')
plt.ylabel('Rate Adequacy')
plt.legend()

# Change in adequacy vs. change in loss ratio
plt.subplot(2, 2, 4)
plt.scatter(df['lr_change'], df['adequacy_change'], alpha=0.5)
plt.axhline(0, color='r', linestyle='--')
plt.axvline(0, color='r', linestyle='--')
plt.title('Change in Loss Ratio vs. Change in Adequacy')
plt.xlabel('Change in Loss Ratio')
plt.ylabel('Change in Rate Adequacy')

plt.tight_layout()
plt.show()
```

## API Reference

::: pyre.rate_monitoring.rate_change

::: pyre.rate_monitoring.rate_adequacy
