# Project 02: Checkout Conversion Experiment

## Overview

This project evaluates a synthetic A/B test of a redesigned e-commerce checkout.

The business question is whether a streamlined checkout should be rolled out based on its impact on:

- checkout conversion
- revenue per checkout user
- technical payment-error risk

The project uses **SQL and Python** to validate the experiment data, build an analysis-ready dataset, calculate product metrics and apply inferential statistics to support a rollout decision.

## Live project

[View the published analysis on GitHub Pages](https://jsklair.github.io/project_02_checkout_ab_test_analysis/)

## Key result

The redesigned checkout increased conversion from **59.90% to 61.32%**.

- **Absolute conversion uplift:** +1.42 percentage points
- **Relative uplift:** +2.37%
- **95% CI:** +0.74pp to +2.10pp
- **Two-sided p-value:** 0.000040

Revenue per checkout user increased from **£46.65 to £48.89**, an observed uplift of **£2.24 per user**.

The technical payment-error rate increased by **0.22 percentage points**, but remained below the pre-agreed **+0.5 percentage-point investigation threshold**.

**Recommendation: roll out the redesigned checkout while continuing to monitor technical payment errors.**

![Checkout conversion](visuals/01_checkout_conversion.png)

## Analysis approach

The project covers:

1. experiment design and metric definition
2. synthetic relational data generation
3. data-quality validation in SQL
4. duplicate and experiment-window handling
5. creation of a one-row-per-user analysis dataset
6. experiment KPI calculation
7. sample ratio mismatch testing
8. two-sample conversion testing and confidence intervals
9. revenue analysis
10. technical payment-error guardrail analysis
11. device subgroup analysis
12. business recommendation

## Dataset

The synthetic dataset contains four related tables:

| Table | Description |
|---|---|
| `users` | User characteristics including device and acquisition channel |
| `experiment_assignments` | Persistent control/treatment assignment |
| `events` | Checkout, payment and purchase events |
| `orders` | Completed orders and revenue |

The experiment contains **80,000 users**, split equally between control and treatment.

Deliberate data-quality issues were included so that the project demonstrates realistic validation and cleaning rather than starting with analysis-ready data.

These include:

- duplicate events
- events outside the experiment window
- missing acquisition-channel values

## Experiment metrics

### Primary metric

**Checkout conversion rate**

Completed purchasers divided by users entering checkout.

### Commercial secondary metric

**Revenue per checkout user**

Total completed-order revenue divided by experiment users entering checkout.

### Guardrail

**Technical payment-error rate**

Users experiencing at least one technical payment error divided by users who submitted payment.

A treatment increase of more than **0.5 percentage points** was pre-agreed as the investigation threshold.

## Results

| Metric | Control | Treatment | Difference |
|---|---:|---:|---:|
| Conversion rate | 59.895% | 61.315% | +1.420pp |
| Revenue per checkout user | £46.65 | £48.89 | +£2.24 |
| Technical payment-error rate | 2.081% | 2.298% | +0.217pp |

The 95% confidence interval for the conversion uplift was **+0.743pp to +2.097pp**, providing strong evidence of a positive treatment effect.

The treatment effect was also positive across both desktop and mobile users.

![Device conversion uplift](visuals/03_device_conversion_uplift.png)

## Repository structure

```text
data/
  synthetic/       Synthetic source CSV files
docs/
  assets/          Images used by the GitHub Pages site
  index.md         Published project landing page
python/
  generate_synthetic_data.py
  build_database.py
  run_sql.py
  analyse_experiment.py
  create_visualisations.py
sql/
  01_data_validation.sql
  02_create_analysis_views.sql
  03_experiment_metrics.sql
reports/
  synthetic_data_specification.md
  experiment_results.md
visuals/
  01_checkout_conversion.png
  02_revenue_per_checkout_user.png
  03_device_conversion_uplift.png
  04_technical_error_guardrail.png
requirements.txt
README.md
project_plan.md
```

The generated SQLite database is deliberately excluded from version control. It can be recreated locally from the supplied CSV files.

## Reproducing the analysis

Install the Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Generate or regenerate the synthetic source data:

```powershell
python python\generate_synthetic_data.py
```

Build the local SQLite database:

```powershell
python python\build_database.py
```

Run the initial SQL validation:

```powershell
python python\run_sql.py sql\01_data_validation.sql
```

Create and validate the analysis views:

```powershell
python python\run_sql.py sql\02_create_analysis_views.sql
```

Calculate the core experiment metrics:

```powershell
python python\run_sql.py sql\03_experiment_metrics.sql
```

Run the statistical analysis:

```powershell
python python\analyse_experiment.py
```

Create the visualisations:

```powershell
python python\create_visualisations.py
```

## Tools

- Python
- pandas
- NumPy
- SciPy
- Matplotlib
- SQL
- SQLite
- Git
- GitHub
- GitHub Pages

## Further detail

See [the full experiment results](reports/experiment_results.md) for the statistical interpretation, guardrail assessment, subgroup analysis and rollout recommendation.

The underlying experiment design and synthetic-data assumptions are documented in [the synthetic data specification](reports/synthetic_data_specification.md).

## Project status

**Complete.**

The dataset is synthetic and is intended to demonstrate a realistic product-analytics and experimentation workflow rather than represent results from a real company.