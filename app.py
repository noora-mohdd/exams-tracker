import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash

os.makedirs("instance", exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-key")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/exams.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

#models

class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(80), nullable=False, unique=True)
    password=db.Column(db.String(50), nullable=False)

    exams=db.relationship("Exam", backref="user", lazy=True)

class Exam(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    exam_name=db.Column(db.String(100), nullable=False)
    exam_type=db.Column(db.String(100))
    exam_date=db.Column(db.Date, nullable=False)
    deadline=db.Column(db.Date, nullable=False)
    notes=db.Column(db.Text)
    link=db.Column(db.String(500))


with app.app_context():
    db.create_all()

#routes
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if User.query.filter_by(username=username).first():
            return "Username already exists"

        user = User(
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    exams = Exam.query.filter_by(user_id=session["user_id"]).order_by(Exam.exam_date).all()
    today = date.today()

    exam_list = []
    for exam in exams:
        days_left = (exam.exam_date - today).days

        if today > exam.exam_date:
            status = "Exam Over"
        elif today > exam.deadline:
            status = "Application Closed"
        else:
            status = "Application Open"

        exam_list.append({
            "id": exam.id,
            "exam_name": exam.exam_name,
            "exam_type": exam.exam_type,
            "exam_date": exam.exam_date,
            "days_left": days_left,
            "status": status,
            "notes": exam.notes,
            "link": exam.link
        })

    return render_template("index.html", exams=exam_list)

@app.route("/add", methods=["GET", "POST"])
def add_exam():
    if request.method == "POST":
        exam = Exam(
            user_id=session["user_id"],
            exam_name=request.form["exam_name"],
            exam_type=request.form["exam_type"],
            exam_date=datetime.strptime(request.form["exam_date"], "%Y-%m-%d").date(),
            deadline=datetime.strptime(request.form["deadline"], "%Y-%m-%d").date(),
            notes=request.form["notes"],
            link=request.form["link"]
        )
        db.session.add(exam)
        db.session.commit()
        return redirect(url_for("index"))

    return render_template("add_exam.html", exam=None)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_exam(id):
    exam = Exam.query.get_or_404(id)

    if exam.user_id != session["user_id"]:
        return redirect(url_for("index"))

    if request.method == "POST":
        exam.exam_name = request.form["exam_name"]
        exam.exam_type = request.form["exam_type"]
        exam.exam_date = datetime.strptime(request.form["exam_date"], "%Y-%m-%d").date()
        exam.deadline = datetime.strptime(request.form["deadline"], "%Y-%m-%d").date()
        exam.notes = request.form["notes"]
        exam.link = request.form["link"]

        db.session.commit()
        return redirect(url_for("index"))

    return render_template("edit_exam.html", exam=exam)

@app.route("/delete/<int:id>")
def delete_exam(id):
    exam = Exam.query.get_or_404(id)

    if exam.user_id == session["user_id"]:
        db.session.delete(exam)
        db.session.commit()

    return redirect(url_for("index"))


# ---------- RUN ----------

if __name__ == "__main__":
    app.run(debug=True)
