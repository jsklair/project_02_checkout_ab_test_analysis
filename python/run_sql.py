from pathlib import Path
import sqlite3
import sys

import pandas as pd


# Build project paths relative to this script so the runner is portable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "database" / "checkout_experiment.db"


# The SQL file is supplied when the script is run.
if len(sys.argv) != 2:
    raise SystemExit(
        "Usage: python python/run_sql.py <sql_file>"
    )

sql_path = PROJECT_ROOT / sys.argv[1]

if not sql_path.exists():
    raise FileNotFoundError(f"SQL file not found: {sql_path}")


# Read the SQL file and execute each statement separately so SELECT results
# can be displayed in the terminal.
sql_text = sql_path.read_text(encoding="utf-8")

statements = [
    statement.strip()
    for statement in sql_text.split(";")
    if statement.strip()
]


with sqlite3.connect(DATABASE_PATH) as connection:
    for number, statement in enumerate(statements, start=1):
        print()
        print("=" * 70)
        print(f"Query {number}")
        print("=" * 70)

        try:
            result = pd.read_sql_query(statement, connection)
            print(result.to_string(index=False))

        except Exception as error:
            print(f"ERROR: {error}")