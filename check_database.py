import sqlite3
from pathlib import Path

# Find clarity.db in the same folder as this script
database_path = Path(__file__).resolve().parent / "clarity.db"

print("Database exists:", database_path.exists())
print("Database location:", database_path)

# Connect to the database and inspect its contents
with sqlite3.connect(database_path) as connection:
    cursor = connection.cursor()

    # Show all tables
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = cursor.fetchall()
    print("\nTables:", tables)

    # Show all checklist entries
    cursor.execute("""
        SELECT id, title, category, completed
        FROM checklist
        ORDER BY id
    """)

    rows = cursor.fetchall()

    print("\nChecklist entries:")
    for row in rows:
        print(row)

        # Test saving a change to the database
with sqlite3.connect(database_path) as connection:
    connection.execute(
        "UPDATE checklist SET completed = 1 WHERE id = 1"
    )

# Read the value back
with sqlite3.connect(database_path) as connection:
    result = connection.execute(
        "SELECT completed FROM checklist WHERE id = 1"
    ).fetchone()

print("\nTest result for task 1:", result[0])