# Treaty Module

The Treaty module provides tools for modeling reinsurance contracts and layers. It includes classes for representing different types of reinsurance contracts, their metadata, and methods for calculating recoveries.

## Core Classes

### Treaty Data Structure

The module provides a hierarchical structure for representing reinsurance contracts:

- `ContractType`: An enumeration defining different types of reinsurance contracts (Quota Share, Excess of Loss, etc.)
- `ClaimTriggerBasis`: An enumeration defining different claim trigger bases
- `IndexationClauseType`: An enumeration defining different types of indexation clauses
- `RILayer`: Represents a reinsurance layer with properties like attachment points, limits, etc.
- `RIContractMetadata`: Contains metadata about reinsurance contracts
- `RIContract`: Combines metadata and layers to represent a complete reinsurance contract

## Examples

### Creating and Working with Reinsurance Contracts

```python
from pyre.treaty.contracts import RIContract, RIContractMetadata, RILayer, ClaimTriggerBasis, IndexationClauseType
from pyre.treaty.contract_types import ContractType
from datetime import date

# Create contract metadata
metadata = RIContractMetadata(
    contract_id="XL001",
    contract_description="Property Cat XL",
    cedent_name="ABC Insurance",
    trigger_basis=ClaimTriggerBasis.LOSSES_OCCURRING,
    indexation_clause=IndexationClauseType.NONE,
    indexation_margin=0.0,
    inception_date=date(2022, 1, 1),
    expiration_date=date(2022, 12, 31),
    fx_rates={"USD": 1.0, "EUR": 1.1, "GBP": 1.3}
)

# Create a reinsurance layer
layer = RILayer(
    layer_id=1,
    layer_name="First Layer",
    layer_type=ContractType.EXCESS_OF_LOSS,
    occurrence_attachment=10000000,
    occurrence_limit=20000000,
    aggregate_attachment=0,
    aggregate_limit=0,  # Unlimited
    subject_lines_of_business=["Property"],
    subject_lob_exposure_amounts=[100000000],
    full_subject_premium=5000000,
    written_line=1.0,
    signed_line=0.1,  # 10% share
    number_of_reinstatements=1,
    reinstatement_cost={"1": 1.0}  # 100% of premium for first reinstatement
)

# Create a reinsurance contract
contract = RIContract(metadata, [layer])

# Access contract properties
print(f"Contract ID: {contract.contract_meta_data.contract_id}")
print(f"Contract Description: {contract.contract_meta_data.contract_description}")
print(f"Contract Period: {contract.contract_meta_data.inception_date} to {contract.contract_meta_data.expiration_date}")

# Access layer properties
for layer_id in contract.layer_ids():
    layer = contract.layers[layer_id - 1]  # Layer IDs are 1-based
    print(f"Layer {layer.layer_id}: {layer.layer_name}")
    print(f"  Attachment: {layer.occurrence_attachment}")
    print(f"  Limit: {layer.occurrence_limit}")
    print(f"  Written Line Premium: {layer.written_line_premium()}")
    print(f"  Signed Line Premium: {layer.signed_line_premium()}")

# Calculate recovery for a loss
loss_amount = 25000000
layer_recovery = layer.loss_to_layer_fn(loss_amount)
print(f"Recovery for loss of {loss_amount}: {layer_recovery}")
```

### Working with Multiple Layers

```python
from pyre.treaty.contracts import RIContract, RILayer
from pyre.treaty.contract_types import ContractType

# Assuming we have a contract metadata object called 'contract_metadata'

# Create multiple layers for a property cat program
layers = [
    RILayer(
        layer_id=1,
        layer_name="Layer 1: 10m xs 10m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=10000000,
        occurrence_limit=10000000,
        aggregate_attachment=0,
        aggregate_limit=20000000,  # 2 full limit losses
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[100000000],
        full_subject_premium=2000000,
        written_line=1.0,
        signed_line=0.15,  # 15% share
        number_of_reinstatements=1,
        reinstatement_cost={"1": 1.0}
    ),
    RILayer(
        layer_id=2,
        layer_name="Layer 2: 30m xs 20m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=20000000,
        occurrence_limit=30000000,
        aggregate_attachment=0,
        aggregate_limit=60000000,  # 2 full limit losses
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[100000000],
        full_subject_premium=3000000,
        written_line=1.0,
        signed_line=0.1,  # 10% share
        number_of_reinstatements=1,
        reinstatement_cost={"1": 1.0}
    ),
    RILayer(
        layer_id=3,
        layer_name="Layer 3: 50m xs 50m",
        layer_type=ContractType.EXCESS_OF_LOSS,
        occurrence_attachment=50000000,
        occurrence_limit=50000000,
        aggregate_attachment=0,
        aggregate_limit=100000000,  # 2 full limit losses
        subject_lines_of_business=["Property"],
        subject_lob_exposure_amounts=[100000000],
        full_subject_premium=1500000,
        written_line=1.0,
        signed_line=0.05,  # 5% share
        number_of_reinstatements=1,
        reinstatement_cost={"1": 1.0}
    )
]

# Create a reinsurance contract with multiple layers
contract = RIContract(contract_metadata, layers)

# Calculate total premium
total_premium = sum(layer.signed_line_premium() for layer in contract.layers)
print(f"Total premium for all layers: {total_premium}")

# Calculate recovery for a large loss across multiple layers
loss_amount = 75000000
total_recovery = 0
for layer in contract.layers:
    layer_recovery = layer.loss_to_layer_fn(loss_amount)
    total_recovery += layer_recovery
    print(f"Layer {layer.layer_id} recovery: {layer_recovery}")

print(f"Total recovery for loss of {loss_amount}: {total_recovery}")
```

## API Reference

::: pyre.treaty.contracts

::: pyre.treaty.contract_types

::: pyre.treaty.layer_loss_functions