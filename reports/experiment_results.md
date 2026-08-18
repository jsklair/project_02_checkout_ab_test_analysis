# Checkout Conversion Experiment: Results

## Executive summary

The redesigned checkout increased checkout conversion from **59.90% to 61.32%**, an absolute uplift of **1.42 percentage points** and a relative uplift of **2.37%**.

The primary result was statistically significant. The estimated conversion uplift was **+1.42 percentage points**, with a **95% confidence interval of +0.74pp to +2.10pp** and a two-sided p-value of **0.000040**.

Revenue per checkout user also increased, from **£46.65 to £48.89**, an observed improvement of **£2.24 per checkout user**. The 95% confidence interval for this difference was **£1.41 to £3.06**.

The redesigned checkout produced a small increase in technical payment errors, from **2.08% to 2.30% of payment submitters**. The estimated increase was **+0.22 percentage points**, with a 95% confidence interval from **-0.004pp to +0.438pp**. This remained below the pre-agreed **+0.5 percentage-point investigation threshold**.

**Recommendation: roll out the redesigned checkout, while continuing to monitor technical payment-error rates after release.**

---

## Business question

The experiment was designed to answer:

> Does a streamlined checkout increase completed purchases enough to justify rollout without creating an unacceptable increase in technical payment errors?

The Product Manager's decision is whether the treatment experience should replace the existing checkout.

---

## Experiment design

The synthetic experiment contains **80,000 checkout users**, randomly assigned equally between:

- **Control:** existing checkout, 40,000 users
- **Treatment:** redesigned checkout, 40,000 users

Randomisation was stratified by device:

| Device | Control | Treatment |
|---|---:|---:|
| Desktop | 14,000 | 14,000 |
| Mobile | 26,000 | 26,000 |

The experiment ran for **14 days**, from 6 July to 19 July 2026.

The primary metric was **checkout conversion rate**.

The main commercial secondary metric was **revenue per checkout user**.

The principal guardrail was **technical payment-error rate among users who submitted payment**.

The experiment was planned using:

- two-sided testing
- significance level of 5%
- statistical power of 80%
- minimum detectable effect of 1 percentage point
- fixed experiment duration rather than optional early stopping

---

## Data validation and preparation

The raw synthetic data consists of four relational tables:

- `users`
- `experiment_assignments`
- `events`
- `orders`

SQL validation identified the deliberately introduced data-quality issues:

- **1,059 duplicate event rows**
- **2,128 out-of-period event rows**
- **1,529 missing acquisition-channel values**

No orphaned user IDs were found in assignments, events or orders.

After removing duplicate events and excluding events outside the experiment window, the clean event table contained **211,733 events**.

The cleaned purchase events reconciled exactly to the orders table:

- deduplicated in-period purchase events: **50,908**
- orders: **50,908**
- difference: **0**

An analysis-ready SQL view was then created with exactly **one row per randomised user**.

---

## Experiment quality

### Sample ratio mismatch

The observed assignment was exactly:

- Control: 40,000
- Treatment: 40,000

The sample-ratio-mismatch test produced:

- chi-square statistic: **0.0000**
- p-value: **1.0000**

There is therefore no evidence of an allocation problem.

---

## Primary outcome: checkout conversion

| Metric | Control | Treatment |
|---|---:|---:|
| Checkout users | 40,000 | 40,000 |
| Converted users | 23,958 | 24,526 |
| Conversion rate | 59.895% | 61.315% |

Treatment therefore produced:

- **absolute uplift:** +1.420 percentage points
- **relative uplift:** +2.37%
- **95% CI:** +0.743pp to +2.097pp
- **two-sided p-value:** 0.000040

The confidence interval is entirely above zero and the p-value is well below 0.05, providing strong evidence that the redesigned checkout increased conversion.

The observed uplift of 1.42 percentage points is also larger than the planned 1 percentage-point minimum detectable effect. However, the lower confidence bound is below 1 percentage point, so the analysis does not establish with 95% confidence that the true effect itself is at least 1 percentage point.

![Checkout conversion](../visuals/01_checkout_conversion.png)

---

## Commercial outcome: revenue per checkout user

| Metric | Control | Treatment |
|---|---:|---:|
| Orders | 25,134 | 25,774 |
| Total revenue | £1,866,119.39 | £1,955,701.89 |
| Revenue per checkout user | £46.65 | £48.89 |

Observed revenue per checkout user increased by **£2.24**.

A Welch two-sample t-test produced:

- **95% CI for difference:** £1.41 to £3.06
- **two-sided p-value:** <0.000001

This supports the primary conversion result from a commercial perspective.

Across the 40,000 treatment users in the experiment, the observed difference relative to the control revenue-per-user rate corresponds to approximately **£89,600 of additional revenue**.

![Revenue per checkout user](../visuals/02_revenue_per_checkout_user.png)

---

## Technical payment-error guardrail

Technical payment errors were measured among users who submitted payment.

| Metric | Control | Treatment |
|---|---:|---:|
| Payment submitters | 33,741 | 33,773 |
| Users with technical error | 702 | 776 |
| Technical error rate | 2.081% | 2.298% |

The estimated increase was:

- **+0.217 percentage points**
- **95% CI:** -0.004pp to +0.438pp
- **two-sided p-value:** 0.053875

The pre-agreed investigation threshold was an increase of more than **0.5 percentage points**.

The point estimate remains below this threshold and, importantly, the upper end of the 95% confidence interval is also below +0.5 percentage points.

The result is therefore reassuring, although the direction of the point estimate supports continued monitoring after rollout.

![Technical payment-error guardrail](../visuals/04_technical_error_guardrail.png)

---

## Device analysis

The treatment effect was positive for both pre-planned device groups.

| Device | Control conversion | Treatment conversion | Absolute uplift |
|---|---:|---:|---:|
| Desktop | 68.950% | 70.286% | +1.336pp |
| Mobile | 55.019% | 56.485% | +1.465pp |

Desktop:

- 95% CI: +0.258pp to +2.413pp
- p-value: 0.015102

Mobile:

- 95% CI: +0.612pp to +2.319pp
- p-value: 0.000768

The positive direction across both device groups gives useful reassurance that the overall result is not being driven entirely by one device type.

These subgroup results should not be interpreted as proof that the treatment effect is identical across devices. A formal interaction test would be required to make that claim.

![Conversion uplift by device](../visuals/03_device_conversion_uplift.png)

---

## Recommendation

**Roll out the redesigned checkout.**

The conversion result is strong enough to support rollout, and the increase in revenue per checkout user points in the same direction. The technical payment-error increase remained below the pre-agreed investigation threshold, so it does not outweigh the evidence in favour of the redesign.

Technical payment-error rates should still be monitored after release because the treatment rate was directionally higher than control.

---

## Limitations

This project uses synthetic data designed to represent a realistic digital-commerce experiment. The results demonstrate the analytical process and should not be interpreted as findings from a real company.

Revenue is right-skewed, as is common for transactional data. The analysis compares user-level revenue using Welch's t-test; the large randomised sample makes the comparison informative, although a bootstrap analysis could be added in a production setting as a robustness check.

Subgroup analysis was pre-planned for device type, but the experiment was powered around the overall primary metric rather than separate device-level decisions.