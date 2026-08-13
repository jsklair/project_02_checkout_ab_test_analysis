from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
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

VISUALS_DIR = PROJECT_ROOT / "visuals"
VISUALS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Load the analysis-ready experiment data.
# ---------------------------------------------------------------------------

with sqlite3.connect(DATABASE_PATH) as connection:
    experiment = pd.read_sql_query(
        """
        SELECT *
        FROM experiment_user_metrics
        """,
        connection,
    )


control = experiment[
    experiment["variant"] == "control"
].copy()

treatment = experiment[
    experiment["variant"] == "treatment"
].copy()


# ---------------------------------------------------------------------------
# Helper function for differences between two proportions.
# ---------------------------------------------------------------------------

def proportion_difference(
    control_successes,
    control_total,
    treatment_successes,
    treatment_total,
):
    control_rate = control_successes / control_total
    treatment_rate = treatment_successes / treatment_total

    difference = treatment_rate - control_rate

    standard_error = np.sqrt(
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

    margin = stats.norm.ppf(0.975) * standard_error

    return {
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "difference": difference,
        "ci_lower": difference - margin,
        "ci_upper": difference + margin,
    }


# ---------------------------------------------------------------------------
# 1. Checkout conversion by variant
# ---------------------------------------------------------------------------

conversion_rates = (
    experiment
    .groupby("variant")["converted"]
    .mean()
    .reindex(["control", "treatment"])
)

conversion_result = proportion_difference(
    control_successes=control["converted"].sum(),
    control_total=len(control),
    treatment_successes=treatment["converted"].sum(),
    treatment_total=len(treatment),
)

fig, ax = plt.subplots(figsize=(7, 5))

bars = ax.bar(
    ["Control", "Treatment"],
    conversion_rates.values * 100,
)

ax.set_ylabel("Checkout conversion rate (%)")
ax.set_title("Checkout conversion increased with the redesigned checkout")
ax.set_ylim(0, 76)

for bar, rate in zip(bars, conversion_rates.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1,
        f"{rate:.1%}",
        ha="center",
    )

ax.text(
    0.5,
    70,
    (
        f"Uplift: +{conversion_result['difference'] * 100:.2f}pp\n"
        f"95% CI: "
        f"{conversion_result['ci_lower'] * 100:.2f}pp to "
        f"{conversion_result['ci_upper'] * 100:.2f}pp"
    ),
    ha="center",
)

fig.tight_layout()

fig.savefig(
    VISUALS_DIR / "01_checkout_conversion.png",
    dpi=200,
    bbox_inches="tight",
)

plt.close(fig)


# ---------------------------------------------------------------------------
# 2. Revenue per checkout user
# ---------------------------------------------------------------------------

revenue_means = (
    experiment
    .groupby("variant")["total_revenue"]
    .mean()
    .reindex(["control", "treatment"])
)

fig, ax = plt.subplots(figsize=(7, 5))

bars = ax.bar(
    ["Control", "Treatment"],
    revenue_means.values,
)

ax.set_ylabel("Revenue per checkout user (£)")
ax.set_title("Revenue per checkout user increased under treatment")
ax.set_ylim(0, 55)

for bar, value in zip(bars, revenue_means.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.8,
        f"£{value:.2f}",
        ha="center",
    )

revenue_difference = (
    revenue_means["treatment"]
    - revenue_means["control"]
)

ax.text(
    0.5,
    52,
    f"Observed uplift: +£{revenue_difference:.2f} per checkout user",
    ha="center",
)

fig.tight_layout()

fig.savefig(
    VISUALS_DIR / "02_revenue_per_checkout_user.png",
    dpi=200,
    bbox_inches="tight",
)

plt.close(fig)


# ---------------------------------------------------------------------------
# 3. Conversion uplift by device
#
# The chart shows the treatment-minus-control difference and its 95%
# confidence interval. A confidence interval crossing zero would indicate
# substantial uncertainty about the direction of the subgroup effect.
# ---------------------------------------------------------------------------

device_results = []

for device in ["desktop", "mobile"]:
    device_control = control[
        control["device_type"] == device
    ]

    device_treatment = treatment[
        treatment["device_type"] == device
    ]

    result = proportion_difference(
        control_successes=device_control["converted"].sum(),
        control_total=len(device_control),
        treatment_successes=device_treatment["converted"].sum(),
        treatment_total=len(device_treatment),
    )

    device_results.append(
        {
            "device": device.capitalize(),
            "uplift_pp": result["difference"] * 100,
            "ci_lower_pp": result["ci_lower"] * 100,
            "ci_upper_pp": result["ci_upper"] * 100,
        }
    )


device_results = pd.DataFrame(device_results)

lower_errors = (
    device_results["uplift_pp"]
    - device_results["ci_lower_pp"]
)

upper_errors = (
    device_results["ci_upper_pp"]
    - device_results["uplift_pp"]
)

# Plot treatment uplift horizontally so the two device groups are
# compact and the confidence intervals are easy to compare.

# Position the two device groups closer together rather than using
# Matplotlib's default one-unit categorical spacing.
y_positions = np.array([0.35, 0.65])

fig, ax = plt.subplots(figsize=(7, 3.5))

ax.errorbar(
    device_results["uplift_pp"],
    y_positions,
    xerr=[lower_errors, upper_errors],
    fmt="o",
    capsize=6,
)

ax.axvline(
    0,
    linewidth=1,
)

ax.set_yticks(y_positions)
ax.set_yticklabels(device_results["device"])
ax.set_ylim(0, 1)

ax.set_xlabel("Treatment conversion uplift (percentage points)")
ax.set_title("Conversion uplift was positive across both device groups")

ax.set_xlim(-0.25, 2.75)

fig.tight_layout()

fig.savefig(
    VISUALS_DIR / "03_device_conversion_uplift.png",
    dpi=200,
    bbox_inches="tight",
)

plt.close(fig)


# ---------------------------------------------------------------------------
# 4. Technical payment-error guardrail
#
# The pre-agreed investigation threshold is an increase of more than
# 0.5 percentage points in treatment versus control.
# ---------------------------------------------------------------------------

control_submitters = control[
    control["submitted_payment"] == 1
]

treatment_submitters = treatment[
    treatment["submitted_payment"] == 1
]

guardrail_result = proportion_difference(
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

guardrail_difference = (
    guardrail_result["difference"] * 100
)

guardrail_lower = (
    guardrail_result["ci_lower"] * 100
)

guardrail_upper = (
    guardrail_result["ci_upper"] * 100
)

fig, ax = plt.subplots(figsize=(7, 5))

ax.errorbar(
    ["Technical payment errors"],
    [guardrail_difference],
    yerr=[
        [guardrail_difference - guardrail_lower],
        [guardrail_upper - guardrail_difference],
    ],
    fmt="o",
    capsize=6,
)

ax.axhline(
    0,
    linewidth=1,
)

ax.axhline(
    0.5,
    linestyle="--",
    linewidth=1,
)

ax.text(
    0,
    0.52,
    "Pre-agreed investigation threshold: +0.5pp",
    ha="center",
)

ax.set_ylabel("Treatment minus control (percentage points)")
ax.set_title("Technical payment-error increase remained below the guardrail")
ax.set_ylim(-0.2, 0.7)

fig.tight_layout()

fig.savefig(
    VISUALS_DIR / "04_technical_error_guardrail.png",
    dpi=200,
    bbox_inches="tight",
)

plt.close(fig)


print("Visualisations created:")
print("  01_checkout_conversion.png")
print("  02_revenue_per_checkout_user.png")
print("  03_device_conversion_uplift.png")
print("  04_technical_error_guardrail.png")