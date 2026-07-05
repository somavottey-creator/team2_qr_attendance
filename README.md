Click To View The Detail in Our Project Documentation: https://docs.google.com/document/d/1yb5Es6xBD9E0Jpe98mpc1ZfI7a8L1JMK0IEAAxYpvBo/edit?usp=sharing

# Smart QR Code Attendance Tracking System – Digital Attendance System

A lightweight Flask web app that replaces manual roll-call with a fast scan-and-type workflow.

## Features

| Feature | Detail |
|---|---|
| **Name autocomplete** | Type a few letters → matching student names appear; selecting one auto-fills the ID field |
| **ID auto-fill** | Student IDs are pre-loaded from the database — typing a name instantly matches and fills in the corresponding ID |
| **One-scan-per-device** | A browser cookie locks a device after a successful submission; a second scan that day is blocked |
| **Auto-registration** | First-time scan auto-creates the student record so no pre-setup is needed |
| **Dashboard** | View attendance by date, see daily counts, and track attendance rates |
| **Student registry** | Add / remove students and browse per-student attendance history |
| **SQLite backend** | Zero-config — all data lives in `attendance.db` in the project root |

## Quick Start

```bash
# 1. Clone / download the project
cd attendance_system

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python main.py
```

Open **http://localhost:5000** in a browser.

## Project Structure

```
attendance_system/
├── main.py                  # Entry point
├── requirements.txt
├── attendance.db            # Created automatically on first run
└── app/
    ├── __init__.py          # App factory
    ├── database.py          # SQLite layer (students + attendance)
    ├── device.py            # Device-identity cookie helpers
    ├── routes.py            # All Flask routes & API endpoints
    ├── templates/
    │   ├── base.html
    │   ├── index.html       # Scan / mark attendance page
    │   ├── dashboard.html   # Attendance overview
    │   ├── students.html    # Student registry
    │   └── student_history.html
    └── static/
        ├── style.css
        └── scan.js          # Autocomplete + form submission
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Scan / mark attendance page |
| `POST` | `/mark` | Submit attendance (JSON body: `student_id`, `student_name`) |
| `GET` | `/api/autocomplete?q=` | Search students by name |
| `GET` | `/api/student/<id>` | Get student details by ID |
| `GET` | `/dashboard` | Attendance dashboard (optional `?date=YYYY-MM-DD`) |
| `GET` | `/students` | Student registry |
| `POST` | `/students/add` | Add a new student |
| `POST` | `/students/delete/<id>` | Remove a student |
| `GET` | `/students/<id>/history` | Per-student attendance history |
| `GET` | `/api/attendance?date=` | Attendance records as JSON |

## Deployment Notes

- For production, set `app.secret_key` to a strong random string via an environment variable.
- Run behind **gunicorn**: `gunicorn -w 4 "app:create_app()"` (add `gunicorn` to requirements).
- The SQLite file works fine for a single school. For multi-school deployments, swap the DB layer for PostgreSQL.
