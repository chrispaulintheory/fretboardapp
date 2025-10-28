from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # change this to a long random string!

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

# ---------- Database setup ----------
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


def init_scores_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                best_score INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, level),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
init_scores_table()

def get_db():
    return sqlite3.connect(DB_PATH)

# ---------- Routes ----------
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

        hashed = generate_password_hash(password, method='pbkdf2:sha256')

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

    user_id = session["user_id"]

    # Make sure this user still exists
    with get_db() as conn:
        user = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        # User no longer exists (e.g., after DB reset)
        session.clear()
        flash("Your account session is invalid. Please log in again.")
        return redirect(url_for("login"))

    username = user[0]

    # Fetch best scores per level
    with get_db() as conn:
        rows = conn.execute(
            "SELECT level, best_score FROM scores WHERE user_id=? ORDER BY level",
            (user_id,)
        ).fetchall()

    best_scores = {row[0]: row[1] for row in rows}

    return render_template("profile.html", username=username, best_scores=best_scores)

@app.route("/game")
def game():
    if "user_id" not in session:
        flash("Please log in to play.")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # 🧩 Make sure this user still exists (handles deleted DB scenario)
    with get_db() as conn:
        user = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        session.clear()
        flash("Your session is no longer valid. Please log in again.")
        return redirect(url_for("login"))

    username = user[0]

    # 🎯 Default to Level 1 for now (you can expand this later)
    level = 1

    # 🏆 Get the best score for this user and level
    with get_db() as conn:
        row = conn.execute(
            "SELECT best_score FROM scores WHERE user_id=? AND level=?",
            (user_id, level)
        ).fetchone()

    best_score = row[0] if row else 0

    # Render the interval trainer game page
    return render_template("intervals.html", username=username, best_score=best_score)

@app.route("/submit_score", methods=["POST"])
def submit_score():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    level = data.get("level", 1)  # <-- NEW: include level info
    score = data.get("score", 0)
    user_id = session["user_id"]

    with get_db() as conn:
        # Check if this user already has a record for this level
        row = conn.execute(
            "SELECT best_score FROM scores WHERE user_id=? AND level=?",
            (user_id, level)
        ).fetchone()

        if row:
            best = row[0]
            if score > best:
                conn.execute(
                    "UPDATE scores SET best_score=? WHERE user_id=? AND level=?",
                    (score, user_id, level)
                )
                conn.commit()
                print(f"✅ Updated best score: user={user_id}, level={level}, score={score}")
        else:
            conn.execute(
                "INSERT INTO scores (user_id, level, best_score) VALUES (?, ?, ?)",
                (user_id, level, score)
            )
            conn.commit()
            print(f"🆕 Saved first score: user={user_id}, level={level}, score={score}")

    return jsonify({"saved": True, "score": score, "status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)