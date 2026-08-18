# Project 02 Initial Plan

> This document records the initial project design. Final experiment settings, realised results and the rollout recommendation are documented in the [synthetic data specification](reports/synthetic_data_specification.md) and [experiment results](reports/experiment_results.md).

## Project

Checkout Conversion Experiment

## Business question

Should the redesigned checkout be rolled out?

## Scenario

A digital-commerce business is testing a redesigned checkout against the existing checkout using a randomised A/B experiment.

- Control: existing checkout
- Treatment: redesigned checkout
- Primary stakeholder: Product Manager responsible for checkout

## Primary metric

Checkout conversion rate:

users who complete a purchase / users who enter checkout

The primary unit of analysis is the user.

## Secondary commercial metric

Revenue per checkout user:

total revenue from completed orders / users who enter checkout

## Guardrail metric

Technical payment-error rate:

users experiencing at least one technical payment error / users who submit payment

Payment declines and technical payment errors will be treated separately.

## Experiment design

- Random assignment at user level
- Persistent assignment for the duration of the experiment
- 50/50 allocation within device type
- Device type used for stratified randomisation
- Balance checks for important pre-treatment characteristics
- Sample ratio mismatch check before interpreting experiment results

## Statistical design

- Baseline checkout conversion: approximately 60%
- Minimum detectable effect: 1 percentage point
- Fixed-horizon experiment design
- Required sample size and minimum experiment duration will both be considered
- Statistical significance will be interpreted alongside effect size, confidence intervals and commercial significance

## Data

The project will use a synthetic relational dataset designed to represent a realistic checkout experiment.

Planned tables:

- users
- experiment_assignments
- events
- orders

The dataset will include a small number of realistic data-quality issues so that validation and cleaning form part of the analysis.

## Tools

- SQL
- Python
- Git and GitHub

Power BI and Excel are not currently planned because they do not add enough value to this project.

## Planned analysis

1. Validate the experiment data
2. Check assignment ratios and group balance
3. Build user-level experiment metrics
4. Measure checkout conversion
5. Measure revenue per checkout user
6. Assess technical payment-error risk
7. Estimate treatment effects and uncertainty
8. Perform useful subgroup analysis
9. Produce a rollout recommendation
