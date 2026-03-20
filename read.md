# AI Digital Wellbeing & Healthcare Assistant

## Overview
A full-featured AI-powered web application for monitoring lifestyle, digital habits, and health. It provides AI-driven health scores, personalized recommendations, trend analytics, and an intelligent chatbot.

## Tech Stack
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js
- **Backend**: Python Flask
- **Database**: SQLite (MySQL-compatible schema, easily switchable)

## Project Structure
```
app.py                    # Main Flask application (all routes + AI logic)
main.py                   # Entry point
database.db               # SQLite database (auto-created on first run)
templates/
  base.html               # Base layout with sidebar + navigation
  login.html              # Login page
  signup.html             # Sign up page
  dashboard.html          # Main health dashboard
  history.html            # Health records history
  analytics.html          # Analytics with Chart.js charts
  chatbot.html            # AI chatbot interface
static/
  css/style.css           # Custom dark theme styles
```

## Features
1. **User Authentication** — Signup/Login with hashed passwords (Werkzeug)
2. **Health Data Tracking** — Sleep, screen time, mood, exercise, water, work hours
3. **AI Health Score** — Rule-based scoring (0-100) with risk level (Low/Medium/High)
4. **AI Recommendations** — Personalized tips based on health data
5. **AI Chatbot** — NLP-style keyword-based health chatbot
6. **Analytics Dashboard** — Chart.js charts for all health metrics
7. **History Page** — Full health record history with color-coded metrics

## Running the App
- Workflow: `python3 main.py`
- App runs on port 5000

## Database Schema (MySQL-compatible)
```sql
-- Users table
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Health data table
CREATE TABLE health_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  sleep_hours REAL NOT NULL,
  screen_time REAL NOT NULL,
  mood TEXT NOT NULL,
  exercise_minutes INTEGER NOT NULL,
  water_intake REAL NOT NULL,
  work_hours REAL NOT NULL,
  date DATE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages table
CREATE TABLE chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Switching to MySQL
To use MySQL instead of SQLite:
1. Install `pip install pymysql`
2. Replace `sqlite3.connect(DATABASE)` with MySQL connection
3. Use same SQL schema (compatible)
