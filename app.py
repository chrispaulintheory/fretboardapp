from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # change this to a long random string!

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# Create table if it doesn't exist
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
init_db()

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("profile"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            flash("Please fill out all fields.")
            return redirect(url_for("register"))

        hashed = generate_password_hash(password)

        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            flash("Registration successful! You can now log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists. Try another.")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            flash("Logged in successfully!")
            return redirect(url_for("profile"))
        else:
            flash("Invalid username or password.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))
    return render_template("profile.html", username=session["username"])

if __name__ == "__main__":
    app.run(debug=True)