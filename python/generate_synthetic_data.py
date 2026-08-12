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

# Generate an assignment timestamp within the 14-day experiment window.
experiment_duration_seconds = int(
    (EXPERIMENT_END + pd.Timedelta(days=1) - EXPERIMENT_START).total_seconds()
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