from flask import Flask, render_template, request, session, redirect, url_for
import os
import mysql.connector

app = Flask(__name__)
app.secret_key = "student_attendance_secret_key"

connection = mysql.connector.connect(
    host=os.environ.get("MYSQLHOST"),
    user=os.environ.get("MYSQLUSER"),
    password=os.environ.get("MYSQLPASSWORD"),
    database=os.environ.get("MYSQLDATABASE")
  
)

cursor = connection.cursor()

print("Database connected successfully!")


@app.route("/")
def home():

    if "user_type" not in session:
        return redirect(url_for("login"))

    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        user_type = request.form["user_type"]

        # Student Login
        if user_type == "student":

            cursor.execute("""
                SELECT student_id, student_name
                FROM students
                WHERE username = %s
                AND password = %s
            """, (username, password))

            student = cursor.fetchone()

            if student:

                session["user_type"] = "student"
                session["student_id"] = student[0]
                session["student_name"] = student[1]

                return redirect(url_for("student_dashboard"))

               

            return "Invalid student username or password!"

        # Teacher Login
        elif user_type == "teacher":

            cursor.execute("""
                SELECT teacher_id, username
                FROM teachers
                WHERE username = %s
                AND password = %s
            """, (username, password))

            teacher = cursor.fetchone()

            if teacher:

                session["user_type"] = "teacher"
                session["teacher_id"] = teacher[0]
                session["username"] = teacher[1]
                return redirect(url_for("teacher_dashboard"))


            return "Invalid teacher username or password!"

    return render_template("login.html")

@app.route("/student-dashboard")
def student_dashboard():

    if "user_type" not in session or session["user_type"] != "student":
        return redirect(url_for("login"))

    return render_template(
        "student_dashboard.html",
        student_name=session["student_name"]
    )
@app.route("/my-attendance")
def my_attendance():

    if "user_type" not in session or session["user_type"] != "student":
        return redirect(url_for("login"))

    student_id = session["student_id"]

    query = """
    SELECT
        sub.subject_name,
        a.attendance_date,
        a.status
    FROM attendance a
    JOIN subjects sub
        ON a.subject_id = sub.subject_id
    WHERE a.student_id = %s
    ORDER BY a.attendance_date DESC
    """

    cursor.execute(query, (student_id,))

    records = cursor.fetchall()

    return render_template(
        "my_attendance.html",
        records=records,
        student_name=session["student_name"]
    )

@app.route("/my-percentage")
def my_percentage():

    if "user_type" not in session or session["user_type"] != "student":
        return redirect(url_for("login"))

    student_id = session["student_id"]

    query = """
    SELECT
        sub.subject_name,
        COUNT(*) AS total_classes,
        SUM(
            CASE
                WHEN LOWER(a.status) = 'present' THEN 1
                ELSE 0
            END
        ) AS attended_classes,
        ROUND(
            SUM(
                CASE
                    WHEN LOWER(a.status) = 'present' THEN 1
                    ELSE 0
                END
            ) * 100.0 / COUNT(*),
            2
        ) AS attendance_percentage

    FROM attendance a

    JOIN subjects sub
        ON a.subject_id = sub.subject_id

    WHERE a.student_id = %s

    GROUP BY sub.subject_name
    """

    cursor.execute(query, (student_id,))

    records = cursor.fetchall()

    return render_template(
        "my_percentage.html",
        records=records,
        student_name=session["student_name"]
    )

@app.route("/my-profile")
def my_profile():

    if "user_type" not in session or session["user_type"] != "student":
        return redirect(url_for("login"))

    student_id = session["student_id"]

    cursor.execute("""
        SELECT student_id, student_name, branch, semester, username
        FROM students
        WHERE student_id = %s
    """, (student_id,))

    student = cursor.fetchone()

    return render_template(
        "my_profile.html",
        student=student
    )

@app.route("/teacher-dashboard")
def teacher_dashboard():

    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))

    # Total students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    # Total attendance records
    cursor.execute("SELECT COUNT(*) FROM attendance")
    total_attendance = cursor.fetchone()[0]

    # Total subjects
    cursor.execute("SELECT COUNT(*) FROM subjects")
    total_subjects = cursor.fetchone()[0]

    return render_template(
        "teacher_dashboard.html",
        username=session["username"],
        total_students=total_students,
        total_attendance=total_attendance,
        total_subjects=total_subjects
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


@app.route("/add-student", methods=["GET", "POST"])
def add_student():
        
    if "user_type" not in session or session["user_type"] != "teacher":
           return redirect(url_for("login"))

    if request.method == "POST":

        print("POST request received!")
        print(request.form)

        student_id = request.form["student_id"]
        student_name = request.form["student_name"]
        branch = request.form["branch"]
        semester = request.form["semester"]

        # Check if Student ID already exists
        cursor.execute(
            "SELECT * FROM students WHERE student_id = %s",
            (student_id,)
        )

        existing_student = cursor.fetchone()

        if existing_student:
            return "Student ID already exists! Please use a different Student ID."

        # Insert new student
        query = """
        INSERT INTO students
        (student_id, student_name, branch, semester)
        VALUES (%s, %s, %s, %s)
        """

        values = (
            student_id,
            student_name,
            branch,
            semester
        )

        cursor.execute(query, values)
        connection.commit()

        return "Student added successfully!"

    return render_template("add_student.html")


@app.route("/mark-attendance", methods=["GET", "POST"])
def mark_attendance():

    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))

    if request.method == "POST":

        student_id = request.form["student_id"]
        subject_id = request.form["subject_id"]
        attendance_date = request.form["attendance_date"]
        status = request.form["status"]

        # Check if attendance is already marked
        cursor.execute("""
            SELECT * FROM attendance
            WHERE student_id = %s
            AND subject_id = %s
            AND attendance_date = %s
        """, (student_id, subject_id, attendance_date))

        existing = cursor.fetchone()

        if existing:
            return "Attendance already marked for this student on this date!"

        # Generate attendance ID
        cursor.execute("SELECT MAX(attendance_id) FROM attendance")
        result = cursor.fetchone()

        if result[0] is None:
            attendance_id = 1
        else:
            attendance_id = result[0] + 1

        # Insert attendance
        query = """
        INSERT INTO attendance
        (attendance_id, student_id, subject_id, attendance_date, status)
        VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            attendance_id,
            student_id,
            subject_id,
            attendance_date,
            status
        )

        cursor.execute(query, values)
        connection.commit()

        return "Attendance marked successfully!"

    # Get students
    cursor.execute("SELECT student_id, student_name FROM students")
    students = cursor.fetchall()

    # Get subjects
    cursor.execute("SELECT subject_id, subject_name FROM subjects")
    subjects = cursor.fetchall()

    return render_template(
        "mark_attendance.html",
        students=students,
        subjects=subjects
    )


@app.route("/delete-student/<int:student_id>")
def delete_student(student_id):

    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))

    # Delete attendance records first
    cursor.execute(
        "DELETE FROM attendance WHERE student_id = %s",
        (student_id,)
    )

    # Then delete the student
    cursor.execute(
        "DELETE FROM students WHERE student_id = %s",
        (student_id,)
    )

    connection.commit()

    return "Student deleted successfully!"


@app.route("/view-attendance")
def view_attendance():

    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))
    
    query = """
    SELECT
        s.student_name,
        sub.subject_name,
        a.attendance_date,
        a.status
    FROM attendance a
    JOIN students s
        ON a.student_id = s.student_id
    JOIN subjects sub
        ON a.subject_id = sub.subject_id
    """

    cursor.execute(query)

    records = cursor.fetchall()

    return render_template("view_attendance.html", records=records)


@app.route("/view-students")
def view_students():

    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))

    search = request.args.get("search", "")

    if search:
        cursor.execute("""
            SELECT student_id, student_name, branch, semester
            FROM students
            WHERE student_name LIKE %s
        """, ("%" + search + "%",))
    else:
        cursor.execute("""
            SELECT student_id, student_name, branch, semester
            FROM students
        """)

    students = cursor.fetchall()

    return render_template(
        "view_students.html",
        students=students,
        search=search
    )

@app.route("/edit-student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):

    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))

    if request.method == "POST":

        student_name = request.form["student_name"]
        branch = request.form["branch"]
        semester = request.form["semester"]

        query = """
        UPDATE students
        SET student_name = %s,
            branch = %s,
            semester = %s
        WHERE student_id = %s
        """

        values = (
            student_name,
            branch,
            semester,
            student_id
        )

        cursor.execute(query, values)
        connection.commit()

        return "Student updated successfully!"

    # Get the existing student details
    cursor.execute("""
        SELECT student_id, student_name, branch, semester
        FROM students
        WHERE student_id = %s
    """, (student_id,))

    student = cursor.fetchone()

    return render_template(
        "edit_student.html",
        student=student
    )

@app.route("/attendance-percentage")
def attendance_percentage():
    if "user_type" not in session or session["user_type"] != "teacher":
        return redirect(url_for("login"))

    query = """
    SELECT
        s.student_name,
        sub.subject_name,
        COUNT(*) AS total_classes,
        SUM(
            CASE
                WHEN LOWER(a.status) = 'present' THEN 1
                ELSE 0
            END
        ) AS attended_classes,
        ROUND(
            SUM(
                CASE
                    WHEN LOWER(a.status) = 'present' THEN 1
                    ELSE 0
                END
            ) * 100.0 / COUNT(*),
            2
        ) AS attendance_percentage
    FROM attendance a
    JOIN students s
        ON a.student_id = s.student_id
    JOIN subjects sub
        ON a.subject_id = sub.subject_id
    GROUP BY s.student_name, sub.subject_name
    """

    cursor.execute(query)

    records = cursor.fetchall()

    return render_template(
        "attendance_percentage.html",
        records=records
    )

if __name__ == "__main__":
    app.run(debug=True)
    



      
