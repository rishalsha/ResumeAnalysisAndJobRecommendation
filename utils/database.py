import sqlite3
import re

def validate_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)

DB_PATH = "InfosysDatabase.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def create_user(name, email, hashed_password, resume_path_file=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (name, email, hashed_password, resume_path_file)
        VALUES (?, ?, ?, ?)
    """, (name, email, hashed_password, resume_path_file))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user

conn=get_connection()

c= conn.cursor()
c.execute(
    """
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL ,
        hashed_password TEXT NOT NULL,
        registration_date TEXT DEFAULT (datetime('now')),
        resume_path_file TEXT
    )
    """
)


c.execute(
    """
        CREATE TABLE IF NOT EXISTS resume_analysis(
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, 
            extracted_resume_text TEXT,
            analysis_score REAL,
            strengths TEXT,
            weaknesses TEXT,
            identified_skills TEXT,
            recommended_skills TEXT,
            analysis_timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
            
        )
    """
)

c.execute(
    """
        CREATE TABLE job_recommendations (
            recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            company_name TEXT,
            location TEXT,
            job_description TEXT,
            job_url TEXT,
            match_percentage REAL,
            scraping_date TEXT DEFAULT (datetime('now')),
            UNIQUE (job_id, user_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )

    """
)

conn.commit()
conn.close()