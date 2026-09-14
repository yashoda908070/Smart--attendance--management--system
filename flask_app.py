from flask import Flask, render_template,request

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/add-student", methods=["GET", "POST"])
def add_student_page():

    if request.method == "POST":
        student_id = request.form["student_id"]
        student_name = request.form["student_name"]
        branch = request.form["branch"]
        semester = request.form["semester"]

        print(student_id, student_name, branch, semester)

    return render_template("add_student.html")

if __name__ == "__main__":
    app.run(debug=True)

