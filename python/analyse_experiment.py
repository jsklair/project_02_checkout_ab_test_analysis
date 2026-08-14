from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "database"
    / "checkout_experiment.db"
)


# ---------------------------------------------------------------------------
# Load the analysis-ready experiment dataset
# ---------------------------------------------------------------------------

with sqlite3.connect(DATABASE_PATH) as connection:
    experiment = pd.read_sql_query(
        """
        SELECT *
        FROM experiment_user_metrics
        """,
        connection,
    )


# ---------------------------------------------------------------------------
# Helper: two-sample proportion test
#
# The z-test assesses whether the observed difference between treatment and
# control is larger than would reasonably be expected from sampling variation.
#
# The confidence interval uses an unpooled standard error because we want an
# interval around the actual difference between the two observed proportions.
# ---------------------------------------------------------------------------

def compare_proportions(
    control_successes,
    control_total,
    treatment_successes,
    treatment_total,
):
    control_rate = control_successes / control_total
    treatment_rate = treatment_successes / treatment_total

    difference = treatment_rate - control_rate

    # Pooled rate is used for the null-hypothesis significance test.
    pooled_rate = (
        control_successes + treatment_successes
    ) / (
        control_total + treatment_total
    )

    pooled_se = np.sqrt(
        pooled_rate
        * (1 - pooled_rate)
        * (
            (1 / control_total)
            + (1 / treatment_total)
        )
    )

    z_statistic = difference / pooled_se

    # Two-sided p-value.
    p_value = 2 * stats.norm.sf(abs(z_statistic))

    # Unpooled standard error for the confidence interval around the difference.
    difference_se = np.sqrt(
        (
            control_rate
            * (1 - control_rate)
            / control_total
        )
        +
        (
            treatment_rate
            * (1 - treatment_rate)
            / treatment_total
        )
    )

    confidence_margin = stats.norm.ppf(0.975) * difference_se

    ci_lower = difference - confidence_margin
    ci_upper = difference + confidence_margin

    return {
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "difference": difference,
        "z_statistic": z_statistic,
        "p_value": p_value,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
    }


# ---------------------------------------------------------------------------
# Split the experiment into control and treatment.
# ---------------------------------------------------------------------------

control = experiment[
    experiment["variant"] == "control"
].copy()

treatment = experiment[
    experiment["variant"] == "treatment"
].copy()


# ---------------------------------------------------------------------------
# 1. Sample ratio mismatch check
#
# The planned allocation was 50/50. A chi-square goodness-of-fit test checks
# whether the observed allocation differs unexpectedly from that design.
# ---------------------------------------------------------------------------

observed_allocation = np.array(
    [len(control), len(treatment)]
)

expected_allocation = np.array(
    [len(experiment) / 2, len(experiment) / 2]
)

srm_statistic, srm_p_value = stats.chisquare(
    observed_allocation,
    expected_allocation,
)


print()
print("=" * 72)
print("1. SAMPLE RATIO MISMATCH CHECK")
print("=" * 72)

print(f"Control users:   {len(control):,}")
print(f"Treatment users: {len(treatment):,}")
print(f"Chi-square statistic: {srm_statistic:.4f}")
print(f"p-value: {srm_p_value:.4f}")


# ---------------------------------------------------------------------------
# 2. Primary metric: checkout conversion rate
# ---------------------------------------------------------------------------

conversion_result = compare_proportions(
    control_successes=control["converted"].sum(),
    control_total=len(control),
    treatment_successes=treatment["converted"].sum(),
    treatment_total=len(treatment),
)


print()
print("=" * 72)
print("2. PRIMARY METRIC: CHECKOUT CONVERSION")
print("=" * 72)

print(
    "Control conversion:   "
    f"{conversion_result['control_rate']:.3%}"
)

print(
    "Treatment conversion: "
    f"{conversion_result['treatment_rate']:.3%}"
)

print(
    "Absolute uplift:      "
    f"{conversion_result['difference'] * 100:.3f} percentage points"
)

relative_uplift = (
    conversion_result["treatment_rate"]
    / conversion_result["control_rate"]
    - 1
) * 100

print(
    "Relative uplift:      "
    f"{relative_uplift:.2f}%"
)

print(
    "95% CI for uplift:    "
    f"{conversion_result['ci_lower'] * 100:.3f}pp "
    f"to {conversion_result['ci_upper'] * 100:.3f}pp"
)

print(
    f"z-statistic:          "
    f"{conversion_result['z_statistic']:.3f}"
)

print(
    f"Two-sided p-value:    "
    f"{conversion_result['p_value']:.6f}"
)


# ---------------------------------------------------------------------------
# 3. Commercial secondary metric: revenue per checkout user
#
# Revenue is right-skewed, but the very large randomised groups make the mean
# comparison informative. Welch's t-test does not assume equal variances.
# ---------------------------------------------------------------------------

control_revenue = control["total_revenue"].to_numpy()
treatment_revenue = treatment["total_revenue"].to_numpy()

revenue_test = stats.ttest_ind(
    treatment_revenue,
    control_revenue,
    equal_var=False,
)

control_revenue_mean = control_revenue.mean()
treatment_revenue_mean = treatment_revenue.mean()

revenue_difference = (
    treatment_revenue_mean
    - control_revenue_mean
)


# Calculate a Welch confidence interval for the difference in means.
control_variance = control_revenue.var(ddof=1)
treatment_variance = treatment_revenue.var(ddof=1)

control_n = len(control_revenue)
treatment_n = len(treatment_revenue)

revenue_se = np.sqrt(
    control_variance / control_n
    + treatment_variance / treatment_n
)

welch_df = (
    (
        control_variance / control_n
        + treatment_variance / treatment_n
    ) ** 2
    /
    (
        (
            (control_variance / control_n) ** 2
            / (control_n - 1)
        )
        +
        (
            (treatment_variance / treatment_n) ** 2
            / (treatment_n - 1)
        )
    )
)

revenue_margin = (
    stats.t.ppf(0.975, welch_df)
    * revenue_se
)

revenue_ci_lower = (
    revenue_difference - revenue_margin
)

revenue_ci_upper = (
    revenue_difference + revenue_margin
)


print()
print("=" * 72)
print("3. REVENUE PER CHECKOUT USER")
print("=" * 72)

print(
    f"Control:   £{control_revenue_mean:.2f}"
)

print(
    f"Treatment: £{treatment_revenue_mean:.2f}"
)

print(
    f"Difference: +£{revenue_difference:.2f}"
)

print(
    "95% CI for difference: "
    f"£{revenue_ci_lower:.2f} "
    f"to £{revenue_ci_upper:.2f}"
)

print(
    f"Welch t-statistic: "
    f"{revenue_test.statistic:.3f}"
)

print(
    f"Two-sided p-value: "
    f"{revenue_test.pvalue:.6f}"
)


# ---------------------------------------------------------------------------
# 4. Technical payment-error guardrail
#
# Only users who submitted payment belong in this denominator.
# ---------------------------------------------------------------------------

control_submitters = control[
    control["submitted_payment"] == 1
]

treatment_submitters = treatment[
    treatment["submitted_payment"] == 1
]

guardrail_result = compare_proportions(
    control_successes=(
        control_submitters[
            "had_technical_payment_error"
        ].sum()
    ),
    control_total=len(control_submitters),
    treatment_successes=(
        treatment_submitters[
            "had_technical_payment_error"
        ].sum()
    ),
    treatment_total=len(treatment_submitters),
)


print()
print("=" * 72)
print("4. TECHNICAL PAYMENT-ERROR GUARDRAIL")
print("=" * 72)

print(
    "Control error rate:   "
    f"{guardrail_result['control_rate']:.3%}"
)

print(
    "Treatment error rate: "
    f"{guardrail_result['treatment_rate']:.3%}"
)

print(
    "Absolute increase:    "
    f"{guardrail_result['difference'] * 100:.3f} percentage points"
)

print(
    "95% CI for difference: "
    f"{guardrail_result['ci_lower'] * 100:.3f}pp "
    f"to {guardrail_result['ci_upper'] * 100:.3f}pp"
)

print(
    f"Two-sided p-value:     "
    f"{guardrail_result['p_value']:.6f}"
)

if guardrail_result["difference"] * 100 > 0.5:
    print("Guardrail status:      INVESTIGATE")
else:
    print(
        "Guardrail status:      "
        "Below +0.5pp investigation threshold"
    )


# ---------------------------------------------------------------------------
# 5. Pre-planned device subgroup analysis
#
# These subgroup results are useful for checking consistency. They should not
# be treated as separate primary experiments.
# ---------------------------------------------------------------------------

print()
print("=" * 72)
print("5. DEVICE SUBGROUP CONVERSION")
print("=" * 72)


for device in ["desktop", "mobile"]:
    device_control = control[
        control["device_type"] == device
    ]

    device_treatment = treatment[
        treatment["device_type"] == device
    ]

    device_result = compare_proportions(
        control_successes=(
            device_control["converted"].sum()
        ),
        control_total=len(device_control),
        treatment_successes=(
            device_treatment["converted"].sum()
        ),
        treatment_total=len(device_treatment),
    )

    print()
    print(device.capitalize())

    print(
        "  Control:   "
        f"{device_result['control_rate']:.3%}"
    )

    print(
        "  Treatment: "
        f"{device_result['treatment_rate']:.3%}"
    )

    print(
        "  Uplift:    "
        f"{device_result['difference'] * 100:.3f}pp"
    )

    print(
        "  95% CI:    "
        f"{device_result['ci_lower'] * 100:.3f}pp "
        f"to {device_result['ci_upper'] * 100:.3f}pp"
    )

    print(
        "  p-value:   "
        f"{device_result['p_value']:.6f}"
    )