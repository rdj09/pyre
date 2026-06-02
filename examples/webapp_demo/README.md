# Shiny App Demo Data

Two CSV files for a complete walk-through of all seven tabs in the pyre Shiny webapp.

## Scenario

**UK Property XL Reinsurance Programme, 2019–2024**

All monetary values are in **£000s** (thousands of pounds).

| Item | Value |
|------|-------|
| Line of business | Commercial Property |
| Currency | GBP |
| Modelling years | 2019–2024 |
| XL contract (enter in UI) | Layer 1: 3,000 xs 2,000 / Layer 2: 5,000 xs 5,000 |
| Gross written premium (exposure) | £45M–£55M p.a. (growing) |
| Claim range (gross incurred) | £3.5M–£12.5M per occurrence |

---

## Files

| File | Use for | Domain type |
|------|---------|-------------|
| `exposures.csv` | Data Loader → Exposure | 6 annual GWP rows, 2019–2024 |
| `claims.csv` | Data Loader → Claim **and** Data Loader → Triangle | 12 claims, accident years 2019–2024 |

---

## Tab-by-Tab Walk-through

### 1. Data Loader

Load exposures first, then claims (loading either clears the other).

**Load exposures:**
1. Upload `exposures.csv`
2. Source type: `csv`
3. Domain type: `Exposure`
4. Click **Load Data**
5. Expected: "Loaded 6 record(s) successfully."

**Load claims:**
1. Upload `claims.csv`
2. Source type: `csv`
3. Domain type: `Claim`
4. Click **Load Data**
5. Expected: "Loaded 12 record(s) successfully."
6. Check the **Summary Statistics** tab — note total latest incurred and modelling years.

> The **Data Preview** and **Domain Objects** tabs show parsed records. The **Summary Statistics**
> tab shows aggregated totals for each domain type.

---

### 2. Triangle

Load the claims CSV as a development triangle (same file, different domain type).

1. Upload `claims.csv` again
2. Source type: `csv`
3. Domain type: `Triangle`
4. Click **Load Data**
5. Expected: "Triangle loaded: 6 origin year(s), 6 development period(s)."

**What to expect — aggregated incurred triangle (£000s):**

| Origin yr | dev 12 | dev 24 | dev 36 | dev 48 | dev 60 | dev 72 |
|-----------|--------|--------|--------|--------|--------|--------|
| 2019 | 7,500 | 8,000 | 8,350 | 8,500 | 8,500 | 8,500 |
| 2020 | 16,500 | 18,500 | 19,800 | 20,500 | 20,500 | — |
| 2021 | 8,800 | 9,600 | 10,000 | 10,200 | — | — |
| 2022 | 14,500 | 18,500 | 20,700 | — | — | — |
| 2023 | 14,200 | 18,700 | — | — | — | — |
| 2024 | 16,300 | — | — | — | — | — |

**Age-to-age factors (volume weighted):**
- 12→24: 1.1919 | 24→36: 1.0778 | 36→48: 1.0275 | 48→60+: 1.0000

The Triangle tab computes ATA factors and IBNER development patterns from these data.
IBNER factors will be non-trivial for the 2022–2024 origin years (still developing).

> **Note:** Reload `claims.csv` as **Claim** (not Triangle) before proceeding to the
> Experience and Simulation tabs — those require the Claims reactive value to be set.

---

### 3. Contract

Enter the two-layer XL programme manually via the form. The app supports 1–5 layers.

**Contract metadata:**
| Field | Value |
|-------|-------|
| Contract ID | PROP-XL-2024 |
| Description | UK Property XL Programme 2024 |
| Cedent name | Demo Insurance Ltd |
| Trigger basis | LOD (Loss occurrence date) |
| Indexation clause | FIC |
| Inception date | 2024-01-01 |
| Expiration date | 2024-12-31 |
| FX rates | GBP:1.0 |
| Year factors | 2019:1.0,2020:1.0,2021:1.0,2022:1.0,2023:1.0,2024:1.0 |

**Layer 1 (XL 3,000 xs 2,000):**
| Field | Value |
|-------|-------|
| Layer name | Layer 1: 3k xs 2k |
| Contract type | Excess of Loss |
| Occurrence attachment | 2000 |
| Occurrence limit | 3000 |
| Aggregate attachment | 0 |
| Aggregate limit | 0 (= unlimited) |
| Subject LOBs | Property |
| Subject LOB exposure amounts | 50000000 |
| Full subject premium | 500000 |
| Written line | 1.0 |
| Signed line | 1.0 |
| Number of reinstatements | 1 |
| Reinstatement cost | 1:1.0 |

**Layer 2 (XL 5,000 xs 5,000):**
| Field | Value |
|-------|-------|
| Layer name | Layer 2: 5k xs 5k |
| Contract type | Excess of Loss |
| Occurrence attachment | 5000 |
| Occurrence limit | 5000 |
| Aggregate attachment | 0 |
| Aggregate limit | 0 (= unlimited) |
| Subject LOBs | Property |
| Subject LOB exposure amounts | 50000000 |
| Full subject premium | 500000 |
| Written line | 1.0 |
| Signed line | 1.0 |
| Number of reinstatements | 1 |
| Reinstatement cost | 1:1.0 |

Click **Build Contract**. Expected: contract summary card showing 2 layers.

> **Alternatively**, upload a pre-built contract JSON. The `build_contract_from_json` API
> accepts the same structure shown in `app/services/model_service.py`.

---

### 4. Experience (Burn Cost)

Requires: Claims loaded + Exposures loaded + Contract built.

**Inputs to enter:**
| Field | Suggested value |
|-------|----------------|
| Layer | Layer 1: 3k xs 2k |
| Projection method (per year) | CHAINLADDER for 2019–2021; BF for 2022–2024 |
| Development pattern | 2019:1.0,2020:1.0,2021:1.02,2022:1.08,2023:1.19,2024:1.50 |
| A priori assumption (BF only) | 2022:0.80,2023:0.80,2024:0.80 |
| Exposure trend factors | 2019:1.0,2020:1.03,2021:1.06,2022:1.09,2023:1.13,2024:1.16 |
| Claim trend factors | 2019:1.0,2020:1.05,2021:1.10,2022:1.16,2023:1.22,2024:1.28 |

**Explanation of development pattern values:** These represent "% of ultimate already observed"
(i.e., how far developed each year is). 2019 = 100% developed; 2024 = ~67% developed.

The burn cost for Layer 1 should be in the range 0.08–0.15 (rate on line), reflecting
that roughly 8–15% of the layer premium goes to losses.

Repeat the analysis for **Layer 2: 5k xs 5k** — the burn cost will be materially lower
since fewer claims breach the 5,000 attachment.

---

### 5. Exposure (Curve Rating)

Requires: Exposures loaded + Contract built.

**MBBEFD curve (moderate industrial property risk):**
| Field | Value |
|-------|-------|
| Curve type | MBBEFD |
| b parameter | 0.25 |
| g parameter | 1.5 |
| Layer | Layer 1: 3k xs 2k |
| Analysis date | 2024-01-01 |

The exposure rate gives the expected loss proportion attributable to the XL layer,
applied against the total insured value in `exposure_values.exposure_value`.

Try switching to **MIXED_EXPONENTIAL** or **RIEBESELL** to compare curve-derived rates.

---

### 6. Rate Adequacy

Standalone calculators — no data load required.

**Adequacy cards:** Enter historical loss ratios and a target combined ratio to compute
the indicated rate change.

**Rate change calculator:** Compound multiple year-on-year rate changes (e.g., +5% then
−3%) to arrive at a cumulative rate level.

---

### 7. Simulation (DFA)

Requires: Claims loaded + Exposures loaded + Contract built + Triangle loaded.

Load the triangle first (see Tab 2), then reload claims as **Claim** (not Triangle) before
navigating here.

**Suggested inputs:**
| Field | Value |
|-------|-------|
| Number of simulations | 5000 |
| Random seed | 42 |
| Frequency distribution | Poisson |
| Mean frequency | 2.5 |
| Severity distribution | Pareto |
| Severity mean | 6500 |
| Severity CV | 1.2 |
| IBNER pattern | Auto-computed from triangle |

The histogram shows the simulated loss distribution for the selected layer. The results
table includes mean, standard deviation, VaR, and TVaR at 95% and 99%.

---

## Data Notes

- **Units:** All monetary values are £000s (e.g., `5000` = £5,000,000).
- **contract_limit = 15,000** in claims: ensures gross claims are uncapped at cedant level.
  The reinsurance layer caps are applied separately by the BurnCostModel.
- **Claims CL-2022, CL-2023, CL-2024** are still open/developing — these drive the IBNER
  pattern in the Triangle tab.
- **Triangle loader** uses `uncapped_claim_development_history` so the `contract_limit`
  in the CSV does not affect triangle values.
- The `exposure_values.attachment_point` and `limit` columns in `exposures.csv` match
  Layer 1 of the XL contract (2,000 xs 2,000) for consistent exposure rating.
