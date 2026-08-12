from pathlib import Path

import numpy as np
import pandas as pd


# Use a fixed seed so the synthetic dataset is reproducible.
RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)


# Core experiment settings.
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

# Funnel behaviour assumptions used to generate checkout journeys.
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

# Build paths relative to this script so the project remains portable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"

# Ensure the output directory exists before any files are written.
SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)


# Create one unique ID for each user in the experiment population.
user_ids = np.arange(1, N_USERS + 1)


# Create the planned 65/35 device mix, then shuffle it across users.
device_types = np.array(
    ["mobile"] * N_MOBILE
    + ["desktop"] * N_DESKTOP
)
rng.shuffle(device_types)


# Assign an acquisition channel to each user using the planned channel mix.
acquisition_channels = rng.choice(
    ACQUISITION_CHANNELS,
    size=N_USERS,
    p=ACQUISITION_PROBABILITIES,
).astype(object)


# Introduce a small proportion of missing acquisition-channel values.
missing_acquisition_mask = (
    rng.random(N_USERS) < MISSING_ACQUISITION_SHARE
)
acquisition_channels[missing_acquisition_mask] = None


# Generate user signup dates across the year before the experiment.
signup_day_offsets = rng.integers(
    0,
    (SIGNUP_END - SIGNUP_START).days + 1,
    size=N_USERS,
)

signup_dates = SIGNUP_START + pd.to_timedelta(
    signup_day_offsets,
    unit="D",
)

# Build the users table from the generated user attributes.
users = pd.DataFrame(
    {
        "user_id": user_ids,
        "signup_date": signup_dates,
        "device_type": device_types,
        "acquisition_channel": acquisition_channels,
    }
)

# Prepare an empty array for each user's experiment assignment.
variants = np.empty(N_USERS, dtype=object)

# Identify the row positions belonging to mobile users.
mobile_indices = np.flatnonzero(device_types == "mobile")

# Shuffle mobile-user positions before splitting them evenly between variants.
rng.shuffle(mobile_indices)

mobile_split = len(mobile_indices) // 2
variants[mobile_indices[:mobile_split]] = "control"
variants[mobile_indices[mobile_split:]] = "treatment"

# Identify and randomly split desktop users evenly between variants.
desktop_indices = np.flatnonzero(device_types == "desktop")
rng.shuffle(desktop_indices)

desktop_split = len(desktop_indices) // 2
variants[desktop_indices[:desktop_split]] = "control"
variants[desktop_indices[desktop_split:]] = "treatment"

# Generate assignment timestamps while leaving time for each checkout journey.
assignment_window_end = (
    EXPERIMENT_END
    + pd.Timedelta(days=1)
    - JOURNEY_BUFFER
)

experiment_duration_seconds = int(
    (assignment_window_end - EXPERIMENT_START).total_seconds()
)

assignment_offsets = rng.integers(
    0,
    experiment_duration_seconds,
    size=N_USERS,
)

assignment_timestamps = EXPERIMENT_START + pd.to_timedelta(
    assignment_offsets,
    unit="s",
)

# Build the experiment assignment table.
experiment_assignments = pd.DataFrame(
    {
        "user_id": user_ids,
        "variant": variants,
        "assignment_timestamp": assignment_timestamps,
    }
)

# Generate whether each user ultimately completes at least one purchase.
converted_mask = np.zeros(N_USERS, dtype=bool)

for (device, variant), conversion_rate in CONVERSION_RATE.items():
    group_mask = (
        (device_types == device)
        & (variants == variant)
    )

    converted_mask[group_mask] = (
        rng.random(group_mask.sum()) < conversion_rate
    )

# Generate payment submission while ensuring every converter submitted payment.
submitted_payment_mask = converted_mask.copy()

for (device, variant), _ in CONVERSION_RATE.items():
    group_mask = (
        (device_types == device)
        & (variants == variant)
    )

    non_converter_mask = group_mask & ~converted_mask

    realised_conversion_rate = converted_mask[group_mask].mean()
    target_submission_rate = PAYMENT_SUBMISSION_RATE[device]

    additional_submission_probability = (
        (target_submission_rate - realised_conversion_rate)
        / (1 - realised_conversion_rate)
    )

    submitted_payment_mask[non_converter_mask] = (
        rng.random(non_converter_mask.sum())
        < additional_submission_probability
    )

# Generate payment declines among users who submitted payment.
payment_declined_mask = np.zeros(N_USERS, dtype=bool)

for device, decline_rate in PAYMENT_DECLINE_RATE.items():
    eligible_mask = (
        (device_types == device)
        & submitted_payment_mask
    )

    payment_declined_mask[eligible_mask] = (
        rng.random(eligible_mask.sum()) < decline_rate
    )

# Generate technical payment errors among users who submitted payment.
technical_error_mask = np.zeros(N_USERS, dtype=bool)

for variant, error_rate in TECHNICAL_ERROR_RATE.items():
    eligible_mask = (
        (variants == variant)
        & submitted_payment_mask
    )

    technical_error_mask[eligible_mask] = (
        rng.random(eligible_mask.sum()) < error_rate
    )

# Build a temporary user-level view to validate the generated funnel outcomes.
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
        ["device_type", "variant"]
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
    ].groupby(
        "device_type"
    )["payment_declined"].mean()
)

print()
print("Technical error rate among submitters by variant:")
print(
    funnel_check.loc[
        funnel_check["submitted_payment"]
    ].groupby(
        "variant"
    )["technical_error"].mean()
)

# Check that no user converts without first submitting payment.
invalid_conversions = (
    converted_mask & ~submitted_payment_mask
).sum()

print()
print(
    "Converters without payment submission:",
    invalid_conversions,
)

# Start the event log with one checkout-started event for every experiment user.
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

# Add a payment-submitted event for each user who reaches payment.
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

    payment_timestamp = assignment_timestamp + pd.Timedelta(
        seconds=int(rng.integers(60, 901))
    )

    first_payment_timestamps[index] = payment_timestamp

    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": payment_timestamp,
            "event_type": "payment_submitted",
        }
    )

# Add decline and technical-error events after the first payment attempt.
last_journey_timestamps = first_payment_timestamps.copy()

for index, user_id in enumerate(user_ids):
    if not submitted_payment_mask[index]:
        continue

    current_timestamp = pd.Timestamp(first_payment_timestamps[index])

    if payment_declined_mask[index]:
        current_timestamp += pd.Timedelta(
            seconds=int(rng.integers(10, 121))
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
            seconds=int(rng.integers(10, 121))
        )

        event_rows.append(
            {
                "user_id": user_id,
                "event_timestamp": current_timestamp,
                "event_type": "technical_payment_error",
            }
        )

    last_journey_timestamps[index] = current_timestamp  

# Add a retry payment submission for converters who experienced a payment failure.
retry_mask = (
    converted_mask
    & (payment_declined_mask | technical_error_mask)
)

for index, user_id in enumerate(user_ids):
    if not retry_mask[index]:
        continue

    retry_timestamp = pd.Timestamp(
        last_journey_timestamps[index]
    ) + pd.Timedelta(
        seconds=int(rng.integers(60, 601))
    )

    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": retry_timestamp,
            "event_type": "payment_submitted",
        }
    )

    last_journey_timestamps[index] = retry_timestamp

# Store first-purchase timestamps for use when building the orders table.
first_purchase_timestamps = np.full(
    N_USERS,
    np.datetime64("NaT"),
    dtype="datetime64[ns]",
)

# Add a purchase-completed event for every user who ultimately converts.
for index, user_id in enumerate(user_ids):
    if not converted_mask[index]:
        continue

    purchase_timestamp = pd.Timestamp(
        last_journey_timestamps[index]
    ) + pd.Timedelta(
        seconds=int(rng.integers(30, 301))
    )

    first_purchase_timestamps[index] = purchase_timestamp

    event_rows.append(
        {
            "user_id": user_id,
            "event_timestamp": purchase_timestamp,
            "event_type": "purchase_completed",
        }
    )

    last_journey_timestamps[index] = purchase_timestamp

# Select repeat purchasers while ensuring their second order can remain in-period.
experiment_cutoff = EXPERIMENT_END + pd.Timedelta(days=1)

repeat_eligible_mask = (
    converted_mask
    & (
        pd.to_datetime(first_purchase_timestamps)
        <= experiment_cutoff - pd.Timedelta(hours=1)
    )
)

repeat_eligible_indices = np.flatnonzero(
    repeat_eligible_mask
)

n_repeat_purchasers = int(
    round(converted_mask.sum() * REPEAT_ORDER_SHARE)
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
repeat_order_mask[repeat_indices] = True

# Generate a second checkout journey for each repeat purchaser.
second_purchase_timestamps = np.full(
    N_USERS,
    np.datetime64("NaT"),
    dtype="datetime64[ns]",
)

for index, user_id in enumerate(user_ids):
    if not repeat_order_mask[index]:
        continue

    second_checkout_timestamp = pd.Timestamp(
        first_purchase_timestamps[index]
    ) + pd.Timedelta(
        seconds=int(rng.integers(600, 1801))
    )

    second_payment_timestamp = second_checkout_timestamp + pd.Timedelta(
        seconds=int(rng.integers(60, 601))
    )

    second_purchase_timestamp = second_payment_timestamp + pd.Timedelta(
        seconds=int(rng.integers(30, 301))
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

    second_purchase_timestamps[index] = second_purchase_timestamp

# Validate the repeat-purchase assumptions before building the events table.
repeat_purchaser_count = repeat_order_mask.sum()
converted_user_count = converted_mask.sum()

print()
print("Converted users:", converted_user_count)
print("Repeat purchasers:", repeat_purchaser_count)
print(
    "Repeat-purchaser share:",
    repeat_purchaser_count / converted_user_count,
)
print(
    "Latest second purchase:",
    pd.to_datetime(second_purchase_timestamps).max(),
)

# Build the events table from the generated event records.
events = pd.DataFrame(event_rows)

events = events.sort_values(
    ["user_id", "event_timestamp", "event_type"]
).reset_index(drop=True)

# Add a unique event ID after all core journey events have been generated.
events.insert(
    0,
    "event_id",
    np.arange(1, len(events) + 1),
)

# Inspect the clean core events table before adding deliberate data-quality issues.
print()
print(events.head(10))

print()
print("Core events shape:", events.shape)

print()
print("Event type counts:")
print(events["event_type"].value_counts())

# Validate core event counts before adding deliberate data-quality issues.
expected_checkout_events = N_USERS + repeat_purchaser_count
expected_purchase_events = converted_user_count + repeat_purchaser_count
expected_payment_events = (
    submitted_payment_mask.sum()
    + retry_mask.sum()
    + repeat_purchaser_count
)

print()
print(
    "Checkout events match expectation:",
    (events["event_type"] == "checkout_started").sum()
    == expected_checkout_events,
)
print(
    "Purchase events match expectation:",
    (events["event_type"] == "purchase_completed").sum()
    == expected_purchase_events,
)
print(
    "Payment-submitted events match expectation:",
    (events["event_type"] == "payment_submitted").sum()
    == expected_payment_events,
)
print(
    "All core events in experiment window:",
    events["event_timestamp"].between(
        EXPERIMENT_START,
        EXPERIMENT_END + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
    ).all(),
)

# Introduce duplicate event records to simulate duplicate ingestion.
DUPLICATE_EVENT_SHARE = 0.005

n_duplicate_events = int(
    round(len(events) * DUPLICATE_EVENT_SHARE)
)

duplicate_indices = rng.choice(
    events.index,
    size=n_duplicate_events,
    replace=False,
)

duplicate_events = events.loc[
    duplicate_indices,
    ["user_id", "event_timestamp", "event_type"],
].copy()

duplicate_events.insert(
    0,
    "event_id",
    np.arange(
        events["event_id"].max() + 1,
        events["event_id"].max() + 1 + n_duplicate_events,
    ),
)

events = pd.concat(
    [events, duplicate_events],
    ignore_index=True,
)

# Validate the deliberately duplicated event records.
duplicate_event_count = events.duplicated(
    subset=["user_id", "event_timestamp", "event_type"],
    keep=False,
).sum()

print()
print("Duplicate rows added:", n_duplicate_events)
print(
    "Rows involved in duplicate event groups:",
    duplicate_event_count,
)

# Introduce out-of-period event records as additional historical/noise data.
OUT_OF_PERIOD_EVENT_SHARE = 0.01

n_out_of_period_events = int(
    round(len(events) * OUT_OF_PERIOD_EVENT_SHARE)
)

out_of_period_indices = rng.choice(
    events.index,
    size=n_out_of_period_events,
    replace=False,
)

out_of_period_events = events.loc[
    out_of_period_indices,
    ["user_id", "event_type"],
].copy()

# Split the noise roughly evenly before and after the experiment window.
before_experiment_mask = (
    rng.random(n_out_of_period_events) < 0.5
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

out_of_period_events["event_timestamp"] = pd.NaT

out_of_period_events.loc[
    before_experiment_mask,
    "event_timestamp",
] = (
    EXPERIMENT_START
    - pd.to_timedelta(
        before_offsets[before_experiment_mask],
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
        after_offsets[~before_experiment_mask],
        unit="s",
    )
)

out_of_period_events.insert(
    0,
    "event_id",
    np.arange(
        events["event_id"].max() + 1,
        events["event_id"].max() + 1 + n_out_of_period_events,
    ),
)

events = pd.concat(
    [events, out_of_period_events],
    ignore_index=True,
)

# Validate the deliberately out-of-period event records.
experiment_end_cutoff = (
    EXPERIMENT_END
    + pd.Timedelta(days=1)
)

out_of_period_mask = (
    (events["event_timestamp"] < EXPERIMENT_START)
    | (events["event_timestamp"] >= experiment_end_cutoff)
)

print()
print(
    "Out-of-period rows added:",
    n_out_of_period_events,
)
print(
    "Out-of-period rows detected:",
    out_of_period_mask.sum(),
)
print(
    "Earliest event timestamp:",
    events["event_timestamp"].min(),
)
print(
    "Latest event timestamp:",
    events["event_timestamp"].max(),
)

# Perform final structural checks on the events table before saving.
print()
print("Final events shape:", events.shape)
print("Unique event IDs:", events["event_id"].nunique())
print("Missing event IDs:", events["event_id"].isna().sum())
print("Missing user IDs:", events["user_id"].isna().sum())
print("Missing event timestamps:", events["event_timestamp"].isna().sum())
print("Missing event types:", events["event_type"].isna().sum())

# Save the completed synthetic events table.
events.to_csv(
    SYNTHETIC_DATA_DIR / "events.csv",
    index=False,
)

# Inspect the experiment assignment table before writing it to disk.
print()
print(experiment_assignments.head())

print()
print("Experiment assignments shape:", experiment_assignments.shape)

# Check that assignment is exactly 50/50 within each device stratum.
assignment_by_device = pd.crosstab(
    users["device_type"],
    experiment_assignments["variant"],
)

print()
print("Assignments by device type:")
print(assignment_by_device)

# Validate assignment uniqueness and experiment-window boundaries.
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

# Save the experiment assignment table.
experiment_assignments.to_csv(
    SYNTHETIC_DATA_DIR / "experiment_assignments.csv",
    index=False,
)

# Inspect the generated users table before writing it to disk.
print(users.head())
print()
print("Users table shape:", users.shape)

# Check that the generated user attributes match the planned distributions.
print()
print("Device type counts:")
print(users["device_type"].value_counts())

print()
print("Acquisition channel counts:")
print(users["acquisition_channel"].value_counts(dropna=False))

print()
print(
    "Missing acquisition channels:",
    users["acquisition_channel"].isna().sum(),
)

# Validate key user-table constraints before saving.
print()
print("Unique user IDs:", users["user_id"].nunique())
print("Minimum signup date:", users["signup_date"].min())
print("Maximum signup date:", users["signup_date"].max())

# Save the generated users table as the first synthetic source file.
users.to_csv(
    SYNTHETIC_DATA_DIR / "users.csv",
    index=False,
)