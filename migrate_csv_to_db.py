# Run this ONCE to move your "student database.csv" into the team's attendance.db
# Run it from inside the project root (same folder as attendance.db).

import csv
import sqlite3

CSV_FILE = "student database.csv"
DB_FILE = "attendance.db"

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

with open(CSV_FILE, mode='r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader, None)  # skip header row
    rows = [
        (row[0].strip(), row[1].strip(), row[2].strip())  # id, name, major -> class_name
        for row in reader if row and len(row) >= 3
    ]

cur.executemany(
    "INSERT OR IGNORE INTO students (id, name, class_name) VALUES (?, ?, ?)",
    rows
)

conn.commit()
print(f"Imported {cur.rowcount} new students (out of {len(rows)} in the CSV).")
conn.close()