"""
Database layer using SQLite.
Handles all data persistence for students and attendance records.
Optimized for atomic transactions and high-performance autocomplete index searches.
"""

import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "attendance.db")


def get_connection():
    """Return a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys support in SQLite explicitly per connection
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create tables and performance indexes if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            class_name  TEXT,
            created_at  TEXT DEFAULT (date('now'))
        )
    """)

    # Performance Index for fast Autocomplete Engine (Case-Insensitive)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_students_name 
        ON students (name COLLATE NOCASE);
    """)

    # Attendance records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   TEXT NOT NULL,
            student_name TEXT NOT NULL,
            date         TEXT NOT NULL,
            device_id    TEXT NOT NULL,
            timestamp    TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (student_id) REFERENCES students(id),
            /* Safeguard: Prevents the same student from being logged multiple times a day */
            UNIQUE(student_id, date) 
        )
    """)

    # Device lock table: tracks which device scanned on which date
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_scans (
            device_id    TEXT NOT NULL,
            scan_date    TEXT NOT NULL,
            student_id   TEXT NOT NULL,
            PRIMARY KEY (device_id, scan_date)
        )
    """)

    conn.commit()
    conn.close()


# ─── Student Operations ───────────────────────────────────────────────────────

def get_all_students():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_by_id(student_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def search_students_by_name(query: str):
    """
    Return students matching query string via optimized Index Prefix Search.
    Only exposes public/safe fields needed for the autocomplete dropdown.
    """
    conn = get_connection()
    # Using 'query%' utilizes the database index for rapid keystroke lookups
    rows = conn.execute(
        "SELECT id, name, class_name FROM students WHERE name LIKE ? ORDER BY name LIMIT 10",
        (f"{query}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_student(student_id: str, name: str, class_name: str = ""):
    """Register a new student. Returns True on success, False if ID exists."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO students (id, name, class_name) VALUES (?, ?, ?)",
            (student_id.strip(), name.strip(), class_name.strip())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_student(student_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()


# ─── Attendance Operations ────────────────────────────────────────────────────

def has_device_scanned_today(device_id: str):
    """Returns True if this device already recorded attendance today."""
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM device_scans WHERE device_id = ? AND scan_date = ?",
        (device_id, today)
    ).fetchone()
    conn.close()
    return row is not None


def record_attendance(student_id: str, student_name: str, device_id: str):
    """
    Mark a student present and lock the device for today securely.
    Guarantees atomic rollback safety if a double-scan race condition occurs.
    """
    today = date.today().isoformat()

    # Pre-flight check: Check if device is locked
    if has_device_scanned_today(device_id):
        return {
            "success": False,
            "message": "This device has already recorded attendance today."
        }

    # Ensure student profile exists
    student = get_student_by_id(student_id)
    if not student:
        add_student(student_id, student_name)

    conn = get_connection()
    try:
        # Wrap everything in a context manager to enforce strict ACID compliance
        with conn:
            # STEP 1: Lock the device FIRST. If this fails due to a rapid double-click, 
            # the code stops here, preventing dummy records from reaching the attendance table.
            conn.execute(
                "INSERT INTO device_scans (device_id, scan_date, student_id) VALUES (?, ?, ?)",
                (device_id, today, student_id)
            )

            # STEP 2: Record formal attendance registry
            conn.execute(
                """INSERT INTO attendance (student_id, student_name, date, device_id)
                   VALUES (?, ?, ?, ?)""",
                (student_id, student_name, today, device_id)
            )

        return {
            "success": True,
            "message": f"Attendance recorded successfully for {student_name}.",
            "record": {
                "student_id": student_id,
                "student_name": student_name,
                "date": today,
                "device_id": device_id
            }
        }
    except sqlite3.IntegrityError as e:
        # Catch dual-student submissions or device lock violations seamlessly
        return {
            "success": False, 
            "message": "Attendance record conflict: Either this device or this student has already checked in today."
        }
    finally:
        conn.close()


def get_attendance_by_date(target_date: str = None):
    if not target_date:
        target_date = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """SELECT a.student_id, a.student_name, a.date, a.device_id, a.timestamp,
                  s.class_name
           FROM attendance a
           LEFT JOIN students s ON a.student_id = s.id
           WHERE a.date = ?
           ORDER BY a.timestamp""",
        (target_date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_attendance_summary():
    conn = get_connection()
    rows = conn.execute(
        """SELECT date, COUNT(*) as count
           FROM attendance
           GROUP BY date
           ORDER BY date DESC
           LIMIT 30"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_attendance_history(student_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? ORDER BY date DESC",
        (student_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]