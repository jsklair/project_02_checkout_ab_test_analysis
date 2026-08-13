from pathlib import Path
import sqlite3

import pandas as pd


# Build paths relative to this script so the project remains portable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
DATABASE_DIR = PROJECT_ROOT / "data" / "database"

DATABASE_PATH = DATABASE_DIR / "checkout_experiment.db"

# Ensure the local database directory exists.
DATABASE_DIR.mkdir(parents=True, exist_ok=True)


# Define the source files and any date/time columns that need parsing.
TABLES = {
    "users": {
        "file": "users.csv",
        "dates": ["signup_date"],
    },
    "experiment_assignments": {
        "file": "experiment_assignments.csv",
        "dates": ["assignment_timestamp"],
    },
    "events": {
        "file": "events.csv",
        "dates": ["event_timestamp"],
    },
    "orders": {
        "file": "orders.csv",
        "dates": ["order_timestamp"],
    },
}


# Load each CSV and write it to SQLite as a table with the same name.
with sqlite3.connect(DATABASE_PATH) as connection:
    for table_name, settings in TABLES.items():
        file_path = SYNTHETIC_DATA_DIR / settings["file"]

        dataframe = pd.read_csv(
            file_path,
            parse_dates=settings["dates"],
        )

        dataframe.to_sql(
            table_name,
            connection,
            if_exists="replace",
            index=False,
        )

        print(
            f"Loaded {table_name}: "
            f"{len(dataframe):,} rows"
        )

    # Add indexes to fields that will be used frequently in joins and filters.
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_assignments_user_id
            ON experiment_assignments(user_id);

        CREATE INDEX IF NOT EXISTS idx_events_user_id
            ON events(user_id);

        CREATE INDEX IF NOT EXISTS idx_events_timestamp
            ON events(event_timestamp);

        CREATE INDEX IF NOT EXISTS idx_orders_user_id
            ON orders(user_id);
        """
    )


print()
print("Database created successfully:")
print(DATABASE_PATH)