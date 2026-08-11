# Synthetic Data Specification

## Purpose

This document defines the synthetic relational dataset used for the Checkout Conversion Experiment.

The dataset is designed to represent a realistic e-commerce A/B test while remaining clearly synthetic.

## Experiment window

Start date:

6 July 2026

End date:

19 July 2026

Duration:

14 days

## Experiment population

Total users:

80,000

Expected allocation:

- Control: 40,000
- Treatment: 40,000

Assignment is persistent at user level.

## Stratified randomisation

Randomisation is stratified by device type.

Device mix:

- Mobile: 65%
- Desktop: 35%

Expected counts:

| Device | Control | Treatment | Total |
|---|---:|---:|---:|
| Mobile | 26,000 | 26,000 | 52,000 |
| Desktop | 14,000 | 14,000 | 28,000 |
| Total | 40,000 | 40,000 | 80,000 |

## Acquisition channels

Expected mix before missing values are introduced:

- Organic: 30%
- Paid search: 25%
- Email: 20%
- Social: 15%
- Affiliate: 10%

Approximately 2% of users will have a missing acquisition channel.

Acquisition channel is not used for stratified randomisation, so small chance imbalances between control and treatment are expected.

## Relational tables

### users

Fields:

- user_id
- signup_date
- device_type
- acquisition_channel

### experiment_assignments

Fields:

- user_id
- variant
- assignment_timestamp

Variant values:

- control
- treatment

Each user should have one persistent experiment assignment.

### events

Fields:

- event_id
- user_id
- event_timestamp
- event_type

Event types:

- checkout_started
- payment_submitted
- payment_declined
- technical_payment_error
- purchase_completed

### orders

Fields:

- order_id
- user_id
- order_timestamp
- order_value

A user may have more than one successful order during the experiment.

## Conversion assumptions

Expected control conversion:

- Mobile: 55.0%
- Desktop: 69.0%

Expected treatment conversion:

- Mobile: 56.2%
- Desktop: 69.6%

Expected uplift:

- Mobile: +1.2 percentage points
- Desktop: +0.6 percentage points
- Overall: approximately +1 percentage point

## Payment submission

Expected percentage of checkout users submitting payment:

- Mobile: 82%
- Desktop: 88%

## Payment declines

Expected decline rate among users who submit payment:

- Mobile: 6%
- Desktop: 4%

These rates should be similar in control and treatment.

## Technical payment-error guardrail

Expected technical payment-error rate among users who submit payment:

- Control: 2.0%
- Treatment: 2.4%

Expected treatment deterioration:

- Absolute: +0.4 percentage points
- Relative: +20%

Predefined investigation threshold:

More than +0.5 percentage points above control.

The threshold is an investigation trigger, not an automatic rollout pass/fail rule.

## Order values

Control and treatment should use the same underlying order-value distribution.

Target average order value:

Approximately £75.

The distribution should be right-skewed:

- most orders roughly £40 to £100;
- some larger orders;
- a small number of substantially higher-value orders.

The treatment should not receive artificially higher order values.

## Repeat orders

Approximately 5% of converted users should place a second successful order during the experiment.

Checkout conversion remains a user-level metric, so repeat purchasers still count once as converted.

Revenue per checkout user includes all successful orders.

## Recovery journeys

Users may recover after a failed payment attempt.

Example decline recovery:

checkout_started
? payment_submitted
? payment_declined
? payment_submitted
? purchase_completed

Example technical-error recovery:

checkout_started
? payment_submitted
? technical_payment_error
? payment_submitted
? purchase_completed

A payment decline or technical error therefore does not automatically mean the user ultimately fails to convert.

## Deliberate data-quality issues

The generated data should include a small number of realistic imperfections.

### Missing acquisition channels

Approximately 2% of users.

### Duplicate event records

Approximately 0.5% of event rows.

Duplicate tracking records should represent the same:

- user_id
- event_timestamp
- event_type

but have a different event_id.

### Out-of-period events

Approximately 1% of event rows should fall outside the 6 July 2026 to 19 July 2026 experiment window.

These should be identified and excluded during experiment validation.

## Statistical design

Baseline conversion:

Approximately 60%.

Minimum detectable effect:

1 percentage point.

Significance level:

5% (alpha = 0.05).

Statistical power:

80%.

Test direction:

Two-sided.

Approximate theoretical sample requirement:

37,500 users per variant.

Operational experiment population:

40,000 users per variant.

The analysis should use effect size, confidence intervals and commercial significance alongside statistical significance.

## Primary metric

Checkout conversion rate:

users completing at least one purchase
/
users entering checkout

Unit of analysis:

user

## Secondary commercial metric

Revenue per checkout user:

total revenue from completed orders
/
users entering checkout

## Guardrail metric

Technical payment-error rate:

users experiencing at least one technical payment error
/
users submitting payment

A user counts once in this guardrail even if multiple technical-error events occur.

## Validation expectations

Before interpreting the treatment effect, the analysis should check:

- experiment assignment counts;
- sample ratio mismatch;
- persistent assignment;
- duplicate events;
- experiment-period boundaries;
- missing acquisition channels;
- device balance;
- acquisition-channel balance;
- event and order reconciliation;
- user-level metric construction.

The analysis should not assume the synthetic source tables are analysis-ready simply because they were generated programmatically.
