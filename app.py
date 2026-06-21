import sqlite3
import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "wellbeing-ai-secret-2024")

DATABASE = "database.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS health_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sleep_hours REAL NOT NULL,
            screen_time REAL NOT NULL,
            mood TEXT NOT NULL,
            exercise_minutes INTEGER NOT NULL,
            water_intake REAL NOT NULL,
            work_hours REAL NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def calculate_health_score(sleep, screen, mood, exercise, water, work):
    if sleep >= 7 and sleep <= 9:
        sleep_score = 100
    elif sleep >= 6:
        sleep_score = 70
    elif sleep >= 5:
        sleep_score = 40
    elif sleep > 9:
        sleep_score = 80
    else:
        sleep_score = 20

    if screen <= 4:
        screen_score = 100
    elif screen <= 6:
        screen_score = 80
    elif screen <= 8:
        screen_score = 55
    elif screen <= 10:
        screen_score = 30
    else:
        screen_score = 10

    if exercise >= 60:
        exercise_score = 100
    elif exercise >= 45:
        exercise_score = 90
    elif exercise >= 30:
        exercise_score = 75
    elif exercise >= 15:
        exercise_score = 50
    elif exercise > 0:
        exercise_score = 30
    else:
        exercise_score = 0

    if water >= 2.5:
        hydration_score = 100
    elif water >= 2.0:
        hydration_score = 85
    elif water >= 1.5:
        hydration_score = 60
    elif water >= 1.0:
        hydration_score = 35
    else:
        hydration_score = 15

    mood_map = {"happy": 100, "neutral": 60, "stressed": 20}
    mood_score = mood_map.get(mood, 60)

    if work <= 6:
        work_score = 100
    elif work <= 8:
        work_score = 80
    elif work <= 10:
        work_score = 50
    else:
        work_score = 20

    score = round(
        sleep_score * 0.25 +
        screen_score * 0.20 +
        exercise_score * 0.20 +
        hydration_score * 0.15 +
        mood_score * 0.10 +
        work_score * 0.10
    )

    risk_level = "Low" if score >= 70 else ("Medium" if score >= 45 else "High")

    recommendations = []
    if sleep_score < 70:
        recommendations.append("Aim for 7-9 hours of quality sleep to restore energy and improve cognition.")
    if screen_score < 55:
        recommendations.append("Reduce screen time — use the 20-20-20 rule: every 20 min, look 20 feet away for 20 sec.")
    if exercise_score < 50:
        recommendations.append("Aim for at least 30 minutes of moderate exercise daily to boost mood and metabolism.")
    if hydration_score < 60:
        recommendations.append("Drink at least 2.5 liters of water daily — set hourly reminders if needed.")
    if mood_score < 50:
        recommendations.append("Practice mindfulness or meditation for 10 minutes daily to manage stress.")
    if work_score < 50:
        recommendations.append("Set clear work boundaries — avoid working more than 8 hours to prevent burnout.")
    if not recommendations:
        recommendations.append("Excellent habits! Keep up your healthy routine and stay consistent.")

    return {
        "score": score,
        "risk_level": risk_level,
        "recommendations": recommendations,
        "breakdown": {
            "sleep": sleep_score,
            "screen_time": screen_score,
            "exercise": exercise_score,
            "hydration": hydration_score,
            "mood": mood_score,
            "work_life": work_score,
        }
    }


def generate_chat_response(message):
    lower = message.lower()

    if any(w in lower for w in ["sleep", "insomnia", "tired", "fatigue"]):
        return ("For better sleep, maintain a consistent schedule even on weekends. Avoid screens 1 hour before bed, "
                "keep your room cool (18-20°C), and try a relaxing routine like reading or gentle stretching. "
                "Adults need 7-9 hours of sleep nightly.")

    if any(w in lower for w in ["stress", "anxious", "anxiety", "worried", "overwhelm"]):
        return ("Try the 4-7-8 breathing: inhale 4 counts, hold 7, exhale 8. Regular exercise, journaling, and "
                "social connection reduce stress significantly. If stress persists, consider speaking with a "
                "mental health professional.")

    if any(w in lower for w in ["exercise", "workout", "fitness", "gym", "walk"]):
        return ("Aim for 150 minutes of moderate aerobic activity per week. Even a 10-minute walk boosts mood. "
                "Start small — consistency beats intensity. Strength training twice a week builds muscle and "
                "bone density.")

    if any(w in lower for w in ["water", "hydration", "drink", "thirsty"]):
        return ("Aim for 8-10 glasses (2-2.5L) of water daily. Your urine should be pale yellow. "
                "Start your morning with a large glass of water and carry a reusable bottle as a reminder.")

    if any(w in lower for w in ["screen", "phone", "digital", "device", "social media"]):
        return ("Use the 20-20-20 rule: every 20 min look at something 20 feet away for 20 seconds. "
                "Enable night mode after sunset, use app timers, and designate tech-free zones. "
                "Consider a 'digital sunset' 1 hour before sleep.")

    if any(w in lower for w in ["diet", "food", "eat", "nutrition", "meal"]):
        return ("Focus on colorful vegetables, lean proteins, healthy fats, and complex carbohydrates. "
                "Limit processed foods and added sugars. Eating mindfully — without distractions — "
                "improves digestion and satisfaction.")

    if any(w in lower for w in ["mood", "happy", "sad", "depress", "emotion"]):
        return ("Mood is influenced by sleep, nutrition, exercise, and social connection. Spend 20 minutes "
                "outdoors daily, practice gratitude (list 3 things daily), and limit social media if it "
                "affects you negatively. Seek professional help if low mood persists.")

    if any(w in lower for w in ["meditation", "mindfulness", "calm", "relax"]):
        return ("Start with 5 minutes of daily meditation — focus on your breath and observe thoughts without "
                "judgment. Apps like Headspace or Insight Timer can guide you. Even mindful walking counts!")

    if any(w in lower for w in ["hello", "hi", "hey", "good morning", "good evening"]):
        return ("Hello! I'm your AI Health Assistant. Ask me about sleep, stress, exercise, nutrition, "
                "hydration, or digital wellness habits. What's on your mind today?")

    if any(w in lower for w in ["thank", "thanks", "appreciate"]):
        return ("You're very welcome! Small consistent steps lead to big health improvements. "
                "I'm always here to support your wellbeing journey!")

    if any(w in lower for w in ["score", "health score", "my score"]):
        return ("Your health score is calculated from 6 factors: sleep (25%), screen time (20%), exercise (20%), "
                "hydration (15%), mood (10%), and work-life balance (10%). Enter your daily data on the dashboard "
                "to get your personalized score!")

    return ("Great health question! Focus on the four pillars: quality sleep (7-9 hrs), regular movement "
            "(30+ min/day), balanced nutrition, and stress management through mindfulness or social connection. "
            "Would you like details on any of these?")


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            return redirect(url_for("dashboard"))
        error = "Invalid email or password. Please try again."
    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            db = get_db()
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                error = "An account with this email already exists."
            else:
                hashed = generate_password_hash(password)
                db.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed))
                db.commit()
                user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                return redirect(url_for("dashboard"))
    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id = session["user_id"]
    records = db.execute(
        "SELECT * FROM health_data WHERE user_id = ? ORDER BY date DESC LIMIT 7",
        (user_id,)
    ).fetchall()
    latest_score = None
    if records:
        r = records[0]
        latest_score = calculate_health_score(
            r["sleep_hours"], r["screen_time"], r["mood"],
            r["exercise_minutes"], r["water_intake"], r["work_hours"]
        )
        latest_score["date"] = r["date"]
    total_records = db.execute(
        "SELECT COUNT(*) as cnt FROM health_data WHERE user_id = ?", (user_id,)
    ).fetchone()["cnt"]
    return render_template("dashboard.html",
                           latest_score=latest_score,
                           records=[dict(r) for r in records],
                           total_records=total_records)


@app.route("/health/submit", methods=["POST"])
@login_required
def submit_health():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    try:
        sleep = float(data["sleep_hours"])
        screen = float(data["screen_time"])
        mood = data["mood"]
        exercise = int(data["exercise_minutes"])
        water = float(data["water_intake"])
        work = float(data["work_hours"])
        date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid data: {e}"}), 400

    db = get_db()
    user_id = session["user_id"]
    existing = db.execute(
        "SELECT id FROM health_data WHERE user_id = ? AND date = ?", (user_id, date)
    ).fetchone()
    if existing:
        db.execute("""
            UPDATE health_data SET sleep_hours=?, screen_time=?, mood=?,
            exercise_minutes=?, water_intake=?, work_hours=? WHERE id=?
        """, (sleep, screen, mood, exercise, water, work, existing["id"]))
    else:
        db.execute("""
            INSERT INTO health_data (user_id, sleep_hours, screen_time, mood, exercise_minutes, water_intake, work_hours, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, sleep, screen, mood, exercise, water, work, date))
    db.commit()
    score = calculate_health_score(sleep, screen, mood, exercise, water, work)
    return jsonify({"success": True, "score": score})


@app.route("/api/health/records")
@login_required
def api_health_records():
    db = get_db()
    user_id = session["user_id"]
    days = int(request.args.get("days", 30))
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    records = db.execute(
        "SELECT * FROM health_data WHERE user_id = ? AND date >= ? ORDER BY date DESC",
        (user_id, cutoff)
    ).fetchall()
    result = []
    for r in records:
        d = dict(r)
        d["score"] = calculate_health_score(
            d["sleep_hours"], d["screen_time"], d["mood"],
            d["exercise_minutes"], d["water_intake"], d["work_hours"]
        )["score"]
        result.append(d)
    return jsonify(result)


@app.route("/api/health/analyze", methods=["POST"])
@login_required
def api_analyze():
    data = request.get_json()
    try:
        result = calculate_health_score(
            float(data["sleep_hours"]),
            float(data["screen_time"]),
            data["mood"],
            int(data["exercise_minutes"]),
            float(data["water_intake"]),
            float(data["work_hours"])
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/history")
@login_required
def history():
    db = get_db()
    user_id = session["user_id"]
    records = db.execute(
        "SELECT * FROM health_data WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    ).fetchall()
    enriched = []
    for r in records:
        d = dict(r)
        score_data = calculate_health_score(
            d["sleep_hours"], d["screen_time"], d["mood"],
            d["exercise_minutes"], d["water_intake"], d["work_hours"]
        )
        d["score"] = score_data["score"]
        d["risk_level"] = score_data["risk_level"]
        enriched.append(d)
    return render_template("history.html", records=enriched)


@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html")


@app.route("/api/analytics/data")
@login_required
def api_analytics():
    db = get_db()
    user_id = session["user_id"]
    days = int(request.args.get("days", 14))
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    records = db.execute(
        "SELECT * FROM health_data WHERE user_id = ? AND date >= ? ORDER BY date ASC",
        (user_id, cutoff)
    ).fetchall()
    result = []
    for r in records:
        d = dict(r)
        score_data = calculate_health_score(
            d["sleep_hours"], d["screen_time"], d["mood"],
            d["exercise_minutes"], d["water_intake"], d["work_hours"]
        )
        d["score"] = score_data["score"]
        d["risk_level"] = score_data["risk_level"]
        result.append(d)
    return jsonify(result)


@app.route("/chatbot")
@login_required
def chatbot():
    db = get_db()
    user_id = session["user_id"]
    messages = db.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC LIMIT 50",
        (user_id,)
    ).fetchall()
    return render_template("chatbot.html", messages=[dict(m) for m in messages])


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message required"}), 400
    response = generate_chat_response(message)
    db = get_db()
    user_id = session["user_id"]
    db.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message))
    db.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'assistant', ?)", (user_id, response))
    db.commit()
    return jsonify({"response": response})


@app.route("/api/chat/clear", methods=["POST"])
@login_required
def api_chat_clear():
    db = get_db()
    db.execute("DELETE FROM chat_messages WHERE user_id = ?", (session["user_id"],))
    db.commit()
    return jsonify({"success": True})

    # ======================================
# AI CAMERA STRESS DETECTION PAGE
# ======================================

@app.route("/stress-detection")
@login_required
def stress_detection():
    return render_template("stress.html")


# ======================================
# AI SYMPTOM DISEASE DETECTION
# ======================================

def detect_disease(symptoms):

    symptoms = [s.lower() for s in symptoms]

    score = {
        "Flu": 0,
        "Common Cold": 0,
        "Migraine": 0
    }

    # Flu symptoms
    if "fever" in symptoms:
        score["Flu"] += 2
    if "cough" in symptoms:
        score["Flu"] += 1
    if "fatigue" in symptoms:
        score["Flu"] += 1

    # Cold symptoms
    if "cough" in symptoms:
        score["Common Cold"] += 1
    if "sore throat" in symptoms:
        score["Common Cold"] += 2

    # Migraine symptoms
    if "headache" in symptoms:
        score["Migraine"] += 2
    if "nausea" in symptoms:
        score["Migraine"] += 1

    disease = max(score, key=score.get)

    if score[disease] == 0:
        return {
            "disease": "Unknown",
            "advice": "Symptoms unclear. Please consult a doctor."
        }

    advice = {
        "Flu": "Rest, drink fluids and monitor your temperature.",
        "Common Cold": "Warm fluids and rest recommended.",
        "Migraine": "Rest in a dark quiet room."
    }

    return {
        "disease": disease,
        "confidence": round(score[disease] / 4 * 100, 2),
        "advice": advice[disease]

    }


@app.route("/symptom-checker")
@login_required
def symptom_checker():
    return render_template("symptom.html")


@app.route("/api/detect-disease", methods=["POST"])
@login_required
def api_detect_disease():

    data = request.get_json()

    symptoms = data.get("symptoms", [])

    result = detect_disease(symptoms)

    return jsonify(result)


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
