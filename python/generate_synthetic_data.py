from pathlib import Path

import numpy as np
import pandas as pd


# Use a fixed seed so the complete synthetic dataset is reproducible.
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)


# ---------------------------------------------------------------------------
# Core experiment settings
# ---------------------------------------------------------------------------

N_USERS = 80_000

EXPERIMENT_START = pd.Timestamp("2026-07-06")
EXPERIMENT_END = pd.Timestamp("2026-07-19")

# Leave enough time for checkout journeys started on the final experiment day.
JOURNEY_BUFFER = pd.Timedelta(hours=2)

SIGNUP_START = pd.Timestamp("2025-07-01")
SIGNUP_END = EXPERIMENT_START - pd.Timedelta(days=1)

MOBILE_SHARE = 0.65
N_MOBILE = int(N_USERS * MOBILE_SHARE)
N_DESKTOP = N_USERS - N_MOBILE

ACQUISITION_CHANNELS = [
    "organic",
    "paid_search",
    "email",
    "social",
    "affiliate",
]

ACQUISITION_PROBABILITIES = [
    0.30,
    0.25,
    0.20,
    0.15,
    0.10,
]

MISSING_ACQUISITION_SHARE = 0.02


# Funnel behaviour assumptions.
PAYMENT_SUBMISSION_RATE = {
    "mobile": 0.82,
    "desktop": 0.88,
}

CONVERSION_RATE = {
    ("mobile", "control"): 0.550,
    ("mobile", "treatment"): 0.562,
    ("desktop", "control"): 0.690,
    ("desktop", "treatment"): 0.696,
}

PAYMENT_DECLINE_RATE = {
    "mobile": 0.06,
    "desktop": 0.04,
}

TECHNICAL_ERROR_RATE = {
    "control": 0.020,
    "treatment": 0.024,
}


# Repeat purchasing assumption.
REPEAT_ORDER_SHARE = 0.05


# Deliberate event-data quality issues.
DUPLICATE_EVENT_SHARE = 0.005
OUT_OF_PERIOD_EVENT_SHARE = 0.01


# Order-value assumptions for a realistic right-skewed distribution.
TARGET_ORDER_VALUE_MEAN = 75.00
ORDER_VALUE_SIGMA = 0.65

ORDER_VALUE_MU = (
    np.log(TARGET_ORDER_VALUE_MEAN)
    - (ORDER_VALUE_SIGMA ** 2) / 2
)


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

# Build paths relative to this script so the project remains portable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"

# Ensure the output directory exists before files are written.
SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Users table
# ---------------------------------------------------------------------------

# Create one unique ID for each experiment user.
user_ids = np.arange(1, N_USERS + 1)


# Create the planned 65/35 device mix, then shuffle it across users.
device_types = np.array(
    ["mobile"] * N_MOBILE
    + ["desktop"] * N_DESKTOP
)

rng.shuffle(device_types)


# Assign acquisition channels using the planned probability mix.
acquisition_channels = rng.choice(
    ACQUISITION_CHANNELS,
    size=N_USERS,
    p=ACQUISITION_PROBABILITIES,
).astype(object)


# Introduce a small proportion of genuinely missing acquisition channels.
missing_acquisition_mask = (
    rng.random(N_USERS) < MISSING_ACQUISITION_SHARE
)

acquisition_channels[missing_acquisition_mask] = None


# Generate signup dates across approximately the year before the experiment.
signup_day_offsets = rng.integers(
    0,
    (SIGNUP_END - SIGNUP_START).days + 1,
    size=N_USERS,
)

signup_dates = SIGNUP_START + pd.to_timedelta(
    signup_day_offsets,
    unit="D",
)


# Build the users table.
users = pd.DataFrame(
    {
        "user_id": user_ids,
        "signup_date": signup_dates,
        "device_type": device_types,
        "acquisition_channel": acquisition_channels,
    }
)


# ---------------------------------------------------------------------------
# Experiment assignments
# ---------------------------------------------------------------------------

# Prepare an array for each user's persistent experiment assignment.
variants = np.empty(
    N_USERS,
    dtype=object,
)


# Randomise mobile users exactly 50/50 between variants.
mobile_indices = np.flatnonzero(
    device_types == "mobile"
)

rng.shuffle(mobile_indices)

mobile_split = len(mobile_indices) // 2

variants[
    mobile_indices[:mobile_split]
] = "control"

variants[
    mobile_indices[mobile_split:]
] = "treatment"


# Randomise desktop users exactly 50/50 between variants.
desktop_indices = np.flatnonzero(
    device_types == "desktop"
)

rng.shuffle(desktop_indices)

desktop_split = len(desktop_indices) // 2

variants[
    desktop_indices[:desktop_split]
] = "control"

variants[
    desktop_indices[desktop_split:]
] = "treatment"


# Generate assignment timestamps while leaving time for checkout journeys.
assignment_window_end = (
    EXPERIMENT_END
    + pd.Timedelta(days=1)
    - JOURNEY_BUFFER
)

experiment_duration_seconds = int(
    (
        assignment_window_end
        - EXPERIMENT_START
    ).total_seconds()
)

assignment_offsets = rng.integers(
    0,
    experiment_duration_seconds,
    size=N_USERS,
)

assignment_timestamps = (
    EXPERIMENT_START
    + pd.to_timedelta(
        assignment_offsets,
        unit="s",
    )
)


# Build the experiment assignments table.
experiment_assignments = pd.DataFrame(
    {
        "user_id": user_ids,
        "variant": variants,
        "assignment_timestamp": assignment_timestamps,
    }
)


# ---------------------------------------------------------------------------
# User-level checkout outcomes
# ---------------------------------------------------------------------------

# Generate whether each user ultimately completes at least one purchase.
converted_mask = np.zeros(
    N_USERS,
    dtype=bool,
)

for (device, variant), conversion_rate in CONVERSION_RATE.items():
    group_mask = (
        (device_types == device)
        & (variants == variant)
    )

    converted_mask[group_mask] = (
        rng.random(group_mask.sum())
        < conversion_rate
    )


# Generate payment submission while ensuring every converter submitted payment.
submitted_payment_mask = converted_mask.copy()

for (device, variant), _ in CONVERSION_RATE.items():
    group_mask = (
        (device_types == device)
        & (variants == variant)
    )

    non_converter_mask = (
        group_mask
        & ~converted_mask
    )

    realised_conversion_rate = (
        converted_mask[group_mask].mean()
    )

    target_submission_rate = (
        PAYMENT_SUBMISSION_RATE[device]
    )

    additional_submission_probability = (
        (
            target_submission_rate
            - realised_conversion_rate
        )
        / (
            1
            - realised_conversion_rate
        )
    )

    submitted_payment_mask[
        non_converter_mask
    ] = (
        rng.random(
            non_converter_mask.sum()
        )
        < additional_submission_probability
    )


# Generate ordinary payment declines among payment submitters.
payment_declined_mask = np.zeros(
    N_USERS,
    dtype=bool,
)

for device, decline_rate in PAYMENT_DECLINE_RATE.items():
    eligible_mask = (
        (device_types == device)
        & submitted_payment_mask
    )

    payment_declined_mask[
        eligible_mask
    ] = (
        rng.random(
            eligible_mask.sum()
        )
        < decline_rate
    )


# Generate technical payment errors among payment submitters.
technical_error_mask = np.zeros(
    N_USERS,
    dtype=bool,
)

for variant, error_rate in TECHNICAL_ERROR_RATE.items():
    eligible_mask = (
        (variants == variant)
        & submitted_payment_mask
    )

    technical_error_mask[
        eligible_mask
    ] = (
        rng.random(
            eligible_mask.sum()
        )
        < error_rate
    )


# ---------------------------------------------------------------------------
# Core checkout event journeys
# ---------------------------------------------------------------------------

# Every experiment user enters checkout at their assignment timestamp.
event_rows = []

for user_id, assignment_timestamp in zip(
    user_ids,
    assignment_timestamps,
):
    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": assignment_timestamp,
            "event_type": "checkout_started",
        }
    )


# Store first-payment timestamps so later journey events remain chronological.
first_payment_timestamps = np.full(
    N_USERS,
    np.datetime64("NaT"),
    dtype="datetime64[ns]",
)


# Add the first payment submission for users who reach payment.
for index, (
    user_id,
    assignment_timestamp,
    submitted_payment,
) in enumerate(
    zip(
        user_ids,
        assignment_timestamps,
        submitted_payment_mask,
    )
):
    if not submitted_payment:
        continue

    payment_timestamp = (
        assignment_timestamp
        + pd.Timedelta(
            seconds=int(
                rng.integers(60, 901)
            )
        )
    )

    first_payment_timestamps[
        index
    ] = payment_timestamp

    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": payment_timestamp,
            "event_type": "payment_submitted",
        }
    )


# Add decline and technical-error events after the first payment attempt.
last_journey_timestamps = (
    first_payment_timestamps.copy()
)

for index, user_id in enumerate(
    user_ids
):
    if not submitted_payment_mask[index]:
        continue

    current_timestamp = pd.Timestamp(
        first_payment_timestamps[index]
    )

    if payment_declined_mask[index]:
        current_timestamp += pd.Timedelta(
            seconds=int(
                rng.integers(10, 121)
            )
        )

        event_rows.append(
            {
                "user_id": user_id,
                "event_timestamp": current_timestamp,
                "event_type": "payment_declined",
            }
        )

    if technical_error_mask[index]:
        current_timestamp += pd.Timedelta(
            seconds=int(
                rng.integers(10, 121)
            )
        )

        event_rows.append(
            {
                "user_id": user_id,
                "event_timestamp": current_timestamp,
                "event_type": "technical_payment_error",
            }
        )

    last_journey_timestamps[
        index
    ] = current_timestamp


# Add a retry submission for converters who experienced a payment failure.
retry_mask = (
    converted_mask
    & (
        payment_declined_mask
        | technical_error_mask
    )
)

for index, user_id in enumerate(
    user_ids
):
    if not retry_mask[index]:
        continue

    retry_timestamp = (
        pd.Timestamp(
            last_journey_timestamps[index]
        )
        + pd.Timedelta(
            seconds=int(
                rng.integers(60, 601)
            )
        )
    )

    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": retry_timestamp,
            "event_type": "payment_submitted",
        }
    )

    last_journey_timestamps[
        index
    ] = retry_timestamp


# Store first successful purchase timestamps for the orders table.
first_purchase_timestamps = np.full(
    N_USERS,
    np.datetime64("NaT"),
    dtype="datetime64[ns]",
)


# Add one successful purchase for every converter.
for index, user_id in enumerate(
    user_ids
):
    if not converted_mask[index]:
        continue

    purchase_timestamp = (
        pd.Timestamp(
            last_journey_timestamps[index]
        )
        + pd.Timedelta(
            seconds=int(
                rng.integers(30, 301)
            )
        )
    )

    first_purchase_timestamps[
        index
    ] = purchase_timestamp

    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": purchase_timestamp,
            "event_type": "purchase_completed",
        }
    )

    last_journey_timestamps[
        index
    ] = purchase_timestamp


# ---------------------------------------------------------------------------
# Repeat purchases
# ---------------------------------------------------------------------------

experiment_cutoff = (
    EXPERIMENT_END
    + pd.Timedelta(days=1)
)


# Only select users with enough time remaining for a second checkout journey.
repeat_eligible_mask = (
    converted_mask
    & (
        pd.to_datetime(
            first_purchase_timestamps
        )
        <= (
            experiment_cutoff
            - pd.Timedelta(hours=1)
        )
    )
)

repeat_eligible_indices = np.flatnonzero(
    repeat_eligible_mask
)

n_repeat_purchasers = int(
    round(
        converted_mask.sum()
        * REPEAT_ORDER_SHARE
    )
)

repeat_indices = rng.choice(
    repeat_eligible_indices,
    size=n_repeat_purchasers,
    replace=False,
)

repeat_order_mask = np.zeros(
    N_USERS,
    dtype=bool,
)

repeat_order_mask[
    repeat_indices
] = True


# Generate a complete second checkout journey for repeat purchasers.
second_purchase_timestamps = np.full(
    N_USERS,
    np.datetime64("NaT"),
    dtype="datetime64[ns]",
)

for index, user_id in enumerate(
    user_ids
):
    if not repeat_order_mask[index]:
        continue

    second_checkout_timestamp = (
        pd.Timestamp(
            first_purchase_timestamps[index]
        )
        + pd.Timedelta(
            seconds=int(
                rng.integers(600, 1801)
            )
        )
    )

    second_payment_timestamp = (
        second_checkout_timestamp
        + pd.Timedelta(
            seconds=int(
                rng.integers(60, 601)
            )
        )
    )

    second_purchase_timestamp = (
        second_payment_timestamp
        + pd.Timedelta(
            seconds=int(
                rng.integers(30, 301)
            )
        )
    )

    event_rows.extend(
        [
            {
                "user_id": user_id,
                "event_timestamp": second_checkout_timestamp,
                "event_type": "checkout_started",
            },
            {
                "user_id": user_id,
                "event_timestamp": second_payment_timestamp,
                "event_type": "payment_submitted",
            },
            {
                "user_id": user_id,
                "event_timestamp": second_purchase_timestamp,
                "event_type": "purchase_completed",
            },
        ]
    )

    second_purchase_timestamps[
        index
    ] = second_purchase_timestamp


# ---------------------------------------------------------------------------
# Events table
# ---------------------------------------------------------------------------

# Build and chronologically sort the clean core event log.
events = pd.DataFrame(
    event_rows
)

events = events.sort_values(
    [
        "user_id",
        "event_timestamp",
        "event_type",
    ]
).reset_index(
    drop=True
)


# Add unique event IDs after all clean journey events have been generated.
events.insert(
    0,
    "event_id",
    np.arange(
        1,
        len(events) + 1,
    ),
)


# Preserve the clean purchase events for later order reconciliation.
core_purchase_events = (
    events.loc[
        events["event_type"]
        == "purchase_completed",
        [
            "user_id",
            "event_timestamp",
        ],
    ]
    .rename(
        columns={
            "event_timestamp": "order_timestamp",
        }
    )
    .copy()
)


# ---------------------------------------------------------------------------
# Deliberate duplicate event records
# ---------------------------------------------------------------------------

# Duplicate a small sample while assigning new event IDs.
n_duplicate_events = int(
    round(
        len(events)
        * DUPLICATE_EVENT_SHARE
    )
)

duplicate_indices = rng.choice(
    events.index,
    size=n_duplicate_events,
    replace=False,
)

duplicate_events = events.loc[
    duplicate_indices,
    [
        "user_id",
        "event_timestamp",
        "event_type",
    ],
].copy()

duplicate_events.insert(
    0,
    "event_id",
    np.arange(
        events["event_id"].max() + 1,
        (
            events["event_id"].max()
            + 1
            + n_duplicate_events
        ),
    ),
)

events = pd.concat(
    [
        events,
        duplicate_events,
    ],
    ignore_index=True,
)


# ---------------------------------------------------------------------------
# Deliberate out-of-period event records
# ---------------------------------------------------------------------------

# Add extra historical/noise events rather than moving core journeys.
n_out_of_period_events = int(
    round(
        len(events)
        * OUT_OF_PERIOD_EVENT_SHARE
    )
)

out_of_period_indices = rng.choice(
    events.index,
    size=n_out_of_period_events,
    replace=False,
)

out_of_period_events = events.loc[
    out_of_period_indices,
    [
        "user_id",
        "event_type",
    ],
].copy()


# Split the noise roughly evenly before and after the experiment.
before_experiment_mask = (
    rng.random(
        n_out_of_period_events
    )
    < 0.5
)

before_offsets = rng.integers(
    1,
    7 * 24 * 60 * 60 + 1,
    size=n_out_of_period_events,
)

after_offsets = rng.integers(
    1,
    7 * 24 * 60 * 60 + 1,
    size=n_out_of_period_events,
)

out_of_period_events[
    "event_timestamp"
] = pd.NaT


out_of_period_events.loc[
    before_experiment_mask,
    "event_timestamp",
] = (
    EXPERIMENT_START
    - pd.to_timedelta(
        before_offsets[
            before_experiment_mask
        ],
        unit="s",
    )
)


out_of_period_events.loc[
    ~before_experiment_mask,
    "event_timestamp",
] = (
    EXPERIMENT_END
    + pd.Timedelta(days=1)
    + pd.to_timedelta(
        after_offsets[
            ~before_experiment_mask
        ],
        unit="s",
    )
)


out_of_period_events.insert(
    0,
    "event_id",
    np.arange(
        events["event_id"].max() + 1,
        (
            events["event_id"].max()
            + 1
            + n_out_of_period_events
        ),
    ),
)

events = pd.concat(
    [
        events,
        out_of_period_events,
    ],
    ignore_index=True,
)


# ---------------------------------------------------------------------------
# Orders table
# ---------------------------------------------------------------------------

# Build exactly one order row for each genuine successful purchase.
order_rows = []

for index, user_id in enumerate(
    user_ids
):
    if converted_mask[index]:
        order_rows.append(
            {
                "user_id": user_id,
                "order_timestamp": first_purchase_timestamps[index],
            }
        )

    if repeat_order_mask[index]:
        order_rows.append(
            {
                "user_id": user_id,
                "order_timestamp": second_purchase_timestamps[index],
            }
        )


orders = pd.DataFrame(
    order_rows
)

orders = orders.sort_values(
    [
        "user_id",
        "order_timestamp",
    ]
).reset_index(
    drop=True
)


# Add a unique order ID.
orders.insert(
    0,
    "order_id",
    np.arange(
        1,
        len(orders) + 1,
    ),
)


# Use the same right-skewed value distribution for all successful orders.
orders["order_value"] = rng.lognormal(
    mean=ORDER_VALUE_MU,
    sigma=ORDER_VALUE_SIGMA,
    size=len(orders),
)

orders["order_value"] = (
    orders["order_value"]
    .round(2)
)


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

print()
print("USERS")
print("-----")
print("Shape:", users.shape)
print("Unique user IDs:", users["user_id"].nunique())
print()
print("Device counts:")
print(users["device_type"].value_counts())
print()
print(
    "Missing acquisition channels:",
    users["acquisition_channel"].isna().sum(),
)


print()
print("EXPERIMENT ASSIGNMENTS")
print("----------------------")

assignment_by_device = pd.crosstab(
    users["device_type"],
    experiment_assignments["variant"],
)

print(assignment_by_device)

print()
print(
    "Unique assigned users:",
    experiment_assignments["user_id"].nunique(),
)

print(
    "Earliest assignment:",
    experiment_assignments["assignment_timestamp"].min(),
)

print(
    "Latest assignment:",
    experiment_assignments["assignment_timestamp"].max(),
)


print()
print("FUNNEL OUTCOMES")
print("---------------")

funnel_check = pd.DataFrame(
    {
        "device_type": device_types,
        "variant": variants,
        "converted": converted_mask,
        "submitted_payment": submitted_payment_mask,
        "payment_declined": payment_declined_mask,
        "technical_error": technical_error_mask,
    }
)

print()
print("Conversion rate by device and variant:")
print(
    funnel_check.groupby(
        [
            "device_type",
            "variant",
        ]
    )["converted"].mean()
)

print()
print("Payment submission rate by device:")
print(
    funnel_check.groupby(
        "device_type"
    )["submitted_payment"].mean()
)

print()
print("Payment decline rate among submitters by device:")
print(
    funnel_check.loc[
        funnel_check["submitted_payment"]
    ]
    .groupby(
        "device_type"
    )["payment_declined"]
    .mean()
)

print()
print("Technical error rate among submitters by variant:")
print(
    funnel_check.loc[
        funnel_check["submitted_payment"]
    ]
    .groupby(
        "variant"
    )["technical_error"]
    .mean()
)


invalid_conversions = (
    converted_mask
    & ~submitted_payment_mask
).sum()

print()
print(
    "Converters without payment submission:",
    invalid_conversions,
)


converted_user_count = (
    converted_mask.sum()
)

repeat_purchaser_count = (
    repeat_order_mask.sum()
)

print(
    "Converted users:",
    converted_user_count,
)

print(
    "Repeat purchasers:",
    repeat_purchaser_count,
)

print(
    "Repeat-purchaser share:",
    repeat_purchaser_count
    / converted_user_count,
)


print()
print("EVENTS")
print("------")

print(
    "Final events shape:",
    events.shape,
)

print(
    "Unique event IDs:",
    events["event_id"].nunique(),
)

duplicate_event_count = events.duplicated(
    subset=[
        "user_id",
        "event_timestamp",
        "event_type",
    ],
    keep=False,
).sum()

print(
    "Duplicate rows added:",
    n_duplicate_events,
)

print(
    "Rows involved in duplicate event groups:",
    duplicate_event_count,
)


experiment_end_cutoff = (
    EXPERIMENT_END
    + pd.Timedelta(days=1)
)

out_of_period_mask = (
    (
        events["event_timestamp"]
        < EXPERIMENT_START
    )
    | (
        events["event_timestamp"]
        >= experiment_end_cutoff
    )
)

print(
    "Out-of-period rows added:",
    n_out_of_period_events,
)

print(
    "Out-of-period rows detected:",
    out_of_period_mask.sum(),
)

print(
    "Missing event IDs:",
    events["event_id"].isna().sum(),
)

print(
    "Missing user IDs:",
    events["user_id"].isna().sum(),
)

print(
    "Missing event timestamps:",
    events["event_timestamp"].isna().sum(),
)

print(
    "Missing event types:",
    events["event_type"].isna().sum(),
)


print()
print("ORDERS")
print("------")

print(
    "Orders shape:",
    orders.shape,
)

print(
    "Unique order IDs:",
    orders["order_id"].nunique(),
)

print(
    "Average order value:",
    round(
        orders["order_value"].mean(),
        2,
    ),
)

print(
    "Median order value:",
    round(
        orders["order_value"].median(),
        2,
    ),
)

print(
    "Maximum order value:",
    round(
        orders["order_value"].max(),
        2,
    ),
)


# Check that every genuine purchase event has exactly one corresponding order.
order_reconciliation = orders.merge(
    core_purchase_events,
    on=[
        "user_id",
        "order_timestamp",
    ],
    how="outer",
    indicator=True,
)

print(
    "Orders matching purchase-completed events:",
    (
        order_reconciliation["_merge"]
        == "both"
    ).sum(),
)

print(
    "Unmatched order/purchase records:",
    (
        order_reconciliation["_merge"]
        != "both"
    ).sum(),
)


# Compare realised order values by variant without forcing them to be identical.
orders_with_variant = orders.merge(
    experiment_assignments[
        [
            "user_id",
            "variant",
        ]
    ],
    on="user_id",
    how="left",
)

print()
print("Average order value by variant:")
print(
    orders_with_variant.groupby(
        "variant"
    )["order_value"].mean()
)


# ---------------------------------------------------------------------------
# Save all four synthetic source tables
# ---------------------------------------------------------------------------

users.to_csv(
    SYNTHETIC_DATA_DIR / "users.csv",
    index=False,
)

experiment_assignments.to_csv(
    SYNTHETIC_DATA_DIR / "experiment_assignments.csv",
    index=False,
)

events.to_csv(
    SYNTHETIC_DATA_DIR / "events.csv",
    index=False,
)

orders.to_csv(
    SYNTHETIC_DATA_DIR / "orders.csv",
    index=False,
)


print()
print("Synthetic data generation complete.")
print("Files written to:")
print(SYNTHETIC_DATA_DIR)