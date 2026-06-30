import csv
import io
import sqlite3
from datetime import datetime
from flask import render_template, request, jsonify, session, redirect, send_file
from app.device import get_device_id, set_device_cookie
from app.database import (
    has_device_scanned_today,
    record_attendance,
    search_students_by_name
)

# ─── CONFIGURATION ───
TEACHER_PASSWORD = "admin"  # Set your desired teacher portal password here


def register_routes(app):
    """Registers endpoints separating the Student Input Portal from the Teacher Admin Center."""
    
    if not app.secret_key:
        app.secret_key = "super_secret_attendance_gate_key"


    # 1. STUDENT LANDING PORTAL (FORM INPUT ONLY)
    @app.route('/')
    def index():
        today_str = datetime.now().strftime("%B %d, %Y")
        
        # ─── FIX: STEP 1: DEVICE DUPLICATION CHECK RUNS FIRST ───
        device_id = get_device_id()
        if has_device_scanned_today(device_id):
            return render_template("index.html", today=today_str, already_scanned=True, error_message=None)


        # ─── STEP 2: TOKEN PARAMETER SECURITY VALIDATIONS ───
        # Guard 1: Verify token param exists from the projector's QR code
        token = request.args.get('token')
        if not token:
            return render_template("index.html", today=today_str, already_scanned=False, error_message="Missing or invalid link. Please scan the live QR code from the classroom projector.")
            
        # Guard 2: Verify sliding security window (Increased to 60s for easier scanning entry)
        try:
            token_time = int(token)
            current_time = int(datetime.now().timestamp())
            if current_time - token_time > 20:
                return render_template("index.html", today=today_str, already_scanned=False, error_message="QR Code expired. Please wait for the teacher's screen to cycle a fresh link and rescan.")
        except ValueError:
            return render_template("index.html", today=today_str, already_scanned=False, error_message="Malformed security tracking token.")


        # ─── STEP 3: RENDER THE FRESH BLANK INPUT FORM ───
        return render_template("index.html", today=today_str, already_scanned=False, error_message=None)


    # 2. STUDENT ATTENDANCE SUBMISSION PIPELINE (NATIVE FORM ENGINE POST HANDLER)
    @app.route('/mark', methods=['POST'])
    def mark_attendance():
        student_ip = request.remote_addr
        today_str = datetime.now().strftime("%B %d, %Y")
        
        print("\n=== [ATTENDANCE INCOMING REQUEST] ===")
        print(f"Device IP Detected: {student_ip}")
        
        # Wi-Fi Subnet Boundary Verification
        SCHOOL_NETWORK_PREFIX = "172.16." 
        if student_ip != "127.0.0.1" and not student_ip.startswith(SCHOOL_NETWORK_PREFIX):
            print(f"❌ SECURITY REJECTION: IP {student_ip} is not on the school subnet.")
            return render_template("index.html", today=today_str, already_scanned=False, error_message=f"Access Denied: Your device IP ({student_ip}) is not on the School Wi-Fi network.")
            
        print("✅ NETWORK PASS: Device verified inside local Wi-Fi parameter pool.")

        # ─── FIX: READ VIA NATIVE POST FORM STRINGS INSTEAD OF JSON ───
        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')
        
        if not student_id or not student_name:
            print("❌ SUBMISSION REJECTION: Missing Form Parameters.")
            return render_template("index.html", today=today_str, already_scanned=False, error_message="Missing input criteria parameters.")
            
        device_id = get_device_id()
        
        # Write structural details directly down to your SQLite database file
        result = record_attendance(student_id, student_name, device_id)
        success = result["success"]
        msg = result["message"]
        if success:
            print(f"💾 DATABASE SUCCESS: Marked {student_name} ({student_id}) Present.")
            # Clear params natively by redirecting to root where Step 1 cookie check will safely lock the screen
            response = redirect('/')
            return set_device_cookie(response, device_id)
        else:
            print(f"❌ DATABASE FAILURE: {msg}")
            return render_template("index.html", today=today_str, already_scanned=False, error_message=f"Database Error: {msg}")


    # 3. TEACHER PORTAL LOGIN ROUTE
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            password = request.form.get('password')
            if password == TEACHER_PASSWORD:
                session['logged_in'] = True
                return redirect('/dashboard')
            else:
                error = "Incorrect administration credentials."
        return render_template("login.html", error=error)


    # 4. TEACHER PORTAL LOGOUT ROUTE
    @app.route('/logout')
    def logout():
        session.pop('logged_in', None)
        return redirect('/login')
    

    # 5. AUTOCOMPLETE ENGINE API (STUDENT-SIDE SUGGESTIONS)
    @app.route('/api/autocomplete', methods=['GET'])
    def autocomplete():
        query = request.args.get('q', '')
        if len(query) < 2:
            return jsonify([])
        results = search_students_by_name(query)
        return jsonify(results)


    # 6. TEACHER-ONLY DASHBOARD (QR CODE ENGINE & STATISTICS)
    @app.route('/dashboard')
    def dashboard():
        if not session.get('logged_in'):
            return redirect('/login')

        selected_date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        try:
            conn = sqlite3.connect("attendance.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM attendance WHERE date(timestamp) = ? ORDER BY timestamp DESC", (selected_date,))
            records = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance WHERE date(timestamp) = ?", (selected_date,))
            present_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM students")
            total_students = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT date(timestamp) as date_str, COUNT(DISTINCT student_id) as day_count FROM attendance GROUP BY date_str ORDER BY date_str DESC LIMIT 30")
            summary = [{"date": row["date_str"], "count": row["day_count"]} for row in cursor.fetchall()]
            
            conn.close()
        except Exception as e:
            print("Dashboard data fetch error:", e)
            records, present_count, total_students, summary = [], 0, 0, []

        return render_template(
            "dashboard.html",
            selected_date=selected_date,
            records=records,
            present_count=present_count,
            total_students=total_students,
            summary=summary
        )


    # 7. TEACHER-ONLY MASTER STUDENT ROSTER MANAGEMENT
    @app.route('/students', methods=['GET', 'POST'])
    def students():
        if not session.get('logged_in'):
            return redirect('/login')
            
        conn = sqlite3.connect("attendance.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if request.method == 'POST':
            student_id = request.form.get('student_id', '').strip()
            student_name = request.form.get('student_name', '').strip()
            class_name = request.form.get('class_name', '').strip()

            if student_id and student_name:
                try:
                    cursor.execute(
                        "INSERT INTO students (student_id, name, class_name) VALUES (?, ?, ?)",
                        (student_id, student_name, class_name)
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    pass 

        cursor.execute("SELECT * FROM students ORDER BY name ASC")
        all_students = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return render_template("students.html", students=all_students)


    # 8. TEACHER PORTAL: EXPORT ATTENDANCE TO CSV
    @app.route('/api/attendance/export')
    def export_csv():
        if not session.get('logged_in'):
            return redirect('/login')

        day = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        try:
            conn = sqlite3.connect("attendance.db")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    student_name AS name, 
                    student_id AS id, 
                    'Present' AS status, 
                    time(timestamp) AS time, 
                    date(timestamp) AS date, 
                    device_id 
                FROM attendance 
                WHERE date(timestamp) = ? 
                ORDER BY timestamp DESC
            """, (day,))
            
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            print("CSV Export database read failure:", e)
            records = []

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["name", "id", "status", "time", "date", "device_id"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)
    
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"attendance_{day}.csv"
        )