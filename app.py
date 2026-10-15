import os
from io import BytesIO
from functools import wraps

import numpy as np
import pandas as pd
import pymysql
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from matplotlib.figure import Figure

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-development-secret")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "student_performance"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

SUBJECTS = ["Mathematics", "Science", "English"]


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def init_db():
    """Create the database tables. Create the database itself before running the app."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    roll_number VARCHAR(30) NOT NULL UNIQUE,
                    full_name VARCHAR(120) NOT NULL,
                    class_name VARCHAR(40) NOT NULL,
                    email VARCHAR(150),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS marks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    subject VARCHAR(80) NOT NULL,
                    marks DECIMAL(5,2) NOT NULL,
                    max_marks DECIMAL(5,2) NOT NULL DEFAULT 100,
                    UNIQUE KEY unique_student_subject (student_id, subject),
                    CONSTRAINT fk_marks_student FOREIGN KEY (student_id)
                        REFERENCES students(id) ON DELETE CASCADE
                )
            """)
        conn.commit()
    finally:
        conn.close()


def fetch_all(query, params=()):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


def execute(query, params=()):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_student_rows():
    return fetch_all("""
        SELECT s.id, s.roll_number, s.full_name, s.class_name, s.email,
               COUNT(m.id) AS subjects_count,
               COALESCE(AVG(m.marks), 0) AS average_marks,
               COALESCE(SUM(m.marks), 0) AS total_marks
        FROM students s LEFT JOIN marks m ON m.student_id = s.id
        GROUP BY s.id
        ORDER BY s.roll_number
    """)


def get_analysis_data():
    rows = fetch_all("""
        SELECT s.id, s.roll_number, s.full_name, s.class_name,
               m.subject, m.marks, m.max_marks
        FROM students s JOIN marks m ON m.student_id = s.id
        ORDER BY s.full_name, m.subject
    """)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["marks"] = pd.to_numeric(df["marks"])
        df["max_marks"] = pd.to_numeric(df["max_marks"])
        df["percentage"] = np.where(df["max_marks"] > 0, df["marks"] / df["max_marks"] * 100, 0)
    return df


@app.route("/")
def dashboard():
    students = get_student_rows()
    df = get_analysis_data()
    total_students = len(students)
    total_records = len(df)
    overall_average = round(float(df["percentage"].mean()), 2) if not df.empty else 0
    pass_percentage = round(float((df["percentage"] >= 35).mean() * 100), 2) if not df.empty else 0
    toppers = []
    low_performers = []
    if not df.empty:
        performance = (df.groupby(["id", "roll_number", "full_name", "class_name"], as_index=False)
                         .agg(average_percentage=("percentage", "mean"), subjects=("subject", "count")))
        performance["average_percentage"] = performance["average_percentage"].round(2)
        toppers = performance.sort_values("average_percentage", ascending=False).head(5).to_dict("records")
        low_performers = performance[performance["average_percentage"] < 50].sort_values("average_percentage").to_dict("records")
    subject_stats = []
    if not df.empty:
        subject_stats = (df.groupby("subject", as_index=False)
                           .agg(average=("percentage", "mean"), entries=("percentage", "count"))
                           .round({"average": 2}).to_dict("records"))
    return render_template("dashboard.html", total_students=total_students,
                           total_records=total_records, overall_average=overall_average,
                           pass_percentage=pass_percentage, toppers=toppers,
                           low_performers=low_performers, subject_stats=subject_stats)


@app.route("/students")
def students():
    return render_template("students.html", students=get_student_rows())


@app.route("/students/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        roll = request.form.get("roll_number", "").strip()
        name = request.form.get("full_name", "").strip()
        class_name = request.form.get("class_name", "").strip()
        email = request.form.get("email", "").strip() or None
        if not all([roll, name, class_name]):
            flash("Roll number, full name, and class are required.", "error")
            return render_template("student_form.html", student=None)
        try:
            execute("INSERT INTO students (roll_number, full_name, class_name, email) VALUES (%s,%s,%s,%s)",
                    (roll, name, class_name, email))
            flash("Student registered successfully.", "success")
            return redirect(url_for("students"))
        except pymysql.err.IntegrityError:
            flash("That roll number already exists. Use a unique roll number.", "error")
        except pymysql.MySQLError as exc:
            app.logger.exception("Unable to register student")
            flash(f"Database error: {exc.args[1] if len(exc.args) > 1 else 'check database settings'}", "error")
    return render_template("student_form.html", student=None)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    student = fetch_all("SELECT * FROM students WHERE id=%s", (student_id,))
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students"))
    student = student[0]
    if request.method == "POST":
        values = (request.form.get("roll_number", "").strip(),
                  request.form.get("full_name", "").strip(),
                  request.form.get("class_name", "").strip(),
                  request.form.get("email", "").strip() or None, student_id)
        if not all(values[:3]):
            flash("Roll number, full name, and class are required.", "error")
        else:
            try:
                execute("UPDATE students SET roll_number=%s, full_name=%s, class_name=%s, email=%s WHERE id=%s", values)
                flash("Student details updated.", "success")
                return redirect(url_for("students"))
            except pymysql.MySQLError:
                flash("Could not update student. Check that the roll number is unique.", "error")
        student.update({"roll_number": values[0], "full_name": values[1],
                        "class_name": values[2], "email": values[3]})
    return render_template("student_form.html", student=student)


@app.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    try:
        execute("DELETE FROM students WHERE id=%s", (student_id,))
        flash("Student and their marks deleted.", "success")
    except pymysql.MySQLError:
        flash("Could not delete student. Check the database connection.", "error")
    return redirect(url_for("students"))


@app.route("/marks")
def marks():
    records = fetch_all("""
        SELECT m.id, s.roll_number, s.full_name, s.class_name, m.subject, m.marks, m.max_marks
        FROM marks m JOIN students s ON s.id=m.student_id
        ORDER BY s.roll_number, m.subject
    """)
    student_options = fetch_all("SELECT id, roll_number, full_name FROM students ORDER BY roll_number")
    return render_template("marks.html", records=records, students=student_options, subjects=SUBJECTS)


@app.route("/marks/add", methods=["POST"])
def add_mark():
    try:
        student_id = int(request.form.get("student_id", ""))
        subject = request.form.get("subject", "").strip()
        marks_value = float(request.form.get("marks", ""))
        max_value = float(request.form.get("max_marks", "100"))
        if subject not in SUBJECTS:
            raise ValueError("Choose a subject from the list.")
        if not np.isfinite(marks_value) or not np.isfinite(max_value) or max_value <= 0 or not 0 <= marks_value <= max_value:
            raise ValueError("Marks must be between 0 and the maximum marks.")
        execute("""
            INSERT INTO marks (student_id, subject, marks, max_marks)
            VALUES (%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE marks=VALUES(marks), max_marks=VALUES(max_marks)
        """, (student_id, subject, marks_value, max_value))
        flash("Marks saved. Existing marks for the same student and subject are updated.", "success")
    except (ValueError, TypeError):
        flash("Invalid marks data. Check the student, subject, and marks.", "error")
    except pymysql.MySQLError:
        app.logger.exception("Unable to save marks")
        flash("Could not save marks. Check the database and ensure the student exists.", "error")
    return redirect(url_for("marks"))


@app.route("/marks/<int:mark_id>/delete", methods=["POST"])
def delete_mark(mark_id):
    try:
        execute("DELETE FROM marks WHERE id=%s", (mark_id,))
        flash("Marks record deleted.", "success")
    except pymysql.MySQLError:
        flash("Could not delete marks record.", "error")
    return redirect(url_for("marks"))


@app.route("/analysis")
def analysis():
    df = get_analysis_data()
    subject_stats, student_stats = [], []
    if not df.empty:
        subject_stats = (df.groupby("subject", as_index=False)
                         .agg(avg_percentage=("percentage", "mean"),
                              highest=("percentage", "max"), lowest=("percentage", "min"),
                              student_count=("percentage", "count"))
                         .round(2).to_dict("records"))
        student_stats = (df.groupby(["id", "roll_number", "full_name", "class_name"], as_index=False)
                         .agg(total_marks=("marks", "sum"), average_percentage=("percentage", "mean"),
                              subjects=("subject", "count")))
        student_stats["average_percentage"] = student_stats["average_percentage"].round(2)
        student_stats["status"] = np.where(student_stats["average_percentage"] >= 35, "Pass", "Needs support")
        student_stats = student_stats.sort_values("average_percentage", ascending=False).to_dict("records")
    return render_template("analysis.html", subject_stats=subject_stats, student_stats=student_stats)


@app.route("/charts/subject-averages.png")
def subject_chart():
    df = get_analysis_data()
    fig = Figure(figsize=(8, 4.5), tight_layout=True)
    ax = fig.subplots()
    if df.empty:
        ax.text(0.5, 0.5, "Add marks to view subject averages", ha="center", va="center")
        ax.set_axis_off()
    else:
        stats = df.groupby("subject")["percentage"].mean().sort_values(ascending=False)
        ax.bar(stats.index, stats.values)
        ax.set_title("Average Percentage by Subject")
        ax.set_ylabel("Average (%)")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", alpha=0.25)
    output = BytesIO()
    fig.savefig(output, format="png", dpi=130)
    output.seek(0)
    return send_file(output, mimetype="image/png")


@app.route("/charts/pass-fail.png")
def pass_fail_chart():
    df = get_analysis_data()
    fig = Figure(figsize=(6, 4), tight_layout=True)
    ax = fig.subplots()
    if df.empty:
        ax.text(0.5, 0.5, "Add marks to view pass percentage", ha="center", va="center")
        ax.set_axis_off()
    else:
        passed = int((df["percentage"] >= 35).sum())
        failed = int((df["percentage"] < 35).sum())
        ax.pie([passed, failed], labels=["Pass (≥35%)", "Below 35%"], autopct="%1.1f%%", startangle=90)
        ax.set_title("Subject Result Distribution")
    output = BytesIO()
    fig.savefig(output, format="png", dpi=130)
    output.seek(0)
    return send_file(output, mimetype="image/png")


@app.route("/export/csv")
def export_csv():
    df = get_analysis_data()
    if df.empty:
        flash("No marks data available to export.", "error")
        return redirect(url_for("analysis"))
    output = BytesIO()
    output.write(df.to_csv(index=False).encode("utf-8-sig"))
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name="student_performance.csv")


@app.route("/health")
def health():
    try:
        fetch_all("SELECT 1 AS ok")
        return {"status": "ok", "database": "connected"}
    except pymysql.MySQLError:
        return {"status": "error", "database": "unavailable"}, 503


if __name__ == "__main__":
    try:
        init_db()
    except pymysql.MySQLError as exc:
        raise SystemExit(
            "Could not connect to MySQL. Create the database and check .env settings first.\n"
            f"Details: {exc}"
        )
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
