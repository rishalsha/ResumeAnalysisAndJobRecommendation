import sqlite3
import bcrypt
import os
import json
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Relative path to the database file
DB_PATH = 'data/database.db'


def get_db_connection():
    # Ensure the parent directories exist before connecting
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        # Ensure resumes folder exists as well
        os.makedirs(os.path.join(db_dir, 'resumes'), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():

    # Ensure data directories exist
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
        os.makedirs(os.path.join(db_dir, 'resumes'), exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resume_file_path TEXT
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        extracted_text TEXT,
        analysis_scores TEXT,
        strengths TEXT,
        weaknesses TEXT,
        identified_skills TEXT,
        recommended_skills TEXT,
        analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    # Ensure one analysis row per user
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_resume_analysis_user_unique ON resume_analysis (user_id)")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        job_title TEXT,
        company_name TEXT,
        location TEXT,
        job_description TEXT,
        job_url TEXT,
        match_percentage REAL,
        scraping_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON resume_analysis (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id_jobs ON job_recommendations (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON users (email)")


    conn.commit()
    conn.close()

def create_user(name, email, password, resume_file_path=None):

    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, resume_file_path) VALUES (?, ?, ?, ?)",
            (name, email, hashed_password, resume_file_path)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()
    return cursor.lastrowid

def get_user_by_email(email):

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def save_resume_analysis(user_id, extracted_text, strengths, weaknesses, skills, suggestions, analysis_scores=None):
    """Save comprehensive resume analysis to database with proper JSON formatting.
    analysis_scores should be a JSON-serializable dict with summary metrics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure all data is properly JSON stringified
        strengths_json = json.dumps(strengths) if isinstance(strengths, (dict, list)) else (strengths if strengths else "{}")
        weaknesses_json = json.dumps(weaknesses) if isinstance(weaknesses, (dict, list)) else (weaknesses if weaknesses else "{}")
        skills_json = json.dumps(skills) if isinstance(skills, (dict, list)) else (skills if skills else "{}")
        suggestions_json = json.dumps(suggestions) if isinstance(suggestions, (dict, list)) else (suggestions if suggestions else "{}")
        
        # Prepare analysis scores JSON (single value or object)
        scores_json = json.dumps(analysis_scores if analysis_scores is not None else {})

        # Validate JSON strings
        try:
            json.loads(strengths_json)
            json.loads(weaknesses_json)
            json.loads(skills_json)
            json.loads(suggestions_json)
            json.loads(scores_json)
        except json.JSONDecodeError as je:
            logger.error(f"JSON validation error: {je}")
            return None
        
        # Upsert to guarantee a single row per user_id
        cursor.execute("""
            INSERT INTO resume_analysis 
            (user_id, extracted_text, strengths, weaknesses, identified_skills, recommended_skills, analysis_scores, analysis_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                extracted_text=excluded.extracted_text,
                strengths=excluded.strengths,
                weaknesses=excluded.weaknesses,
                identified_skills=excluded.identified_skills,
                recommended_skills=excluded.recommended_skills,
                analysis_scores=excluded.analysis_scores,
                analysis_timestamp=CURRENT_TIMESTAMP
        """, (
            user_id,
            extracted_text,
            strengths_json,
            weaknesses_json,
            skills_json,
            suggestions_json,
            scores_json
        ))
        conn.commit()
        analysis_id = cursor.lastrowid
        logger.info(f"Analysis saved successfully for user {user_id}, ID: {analysis_id}")
        return analysis_id
    except Exception as e:
        logger.error(f"Error saving resume analysis: {e}")
        return None
    finally:
        conn.close()

def get_user_analysis(user_id):
    """Retrieve the most recent comprehensive analysis for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, extracted_text, strengths, weaknesses, identified_skills, 
                   recommended_skills, analysis_scores, analysis_timestamp
            FROM resume_analysis
            WHERE user_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT 1
        """, (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "extracted_text": row["extracted_text"],
                "strengths": json.loads(row["strengths"]) if row["strengths"] else {},
                "weaknesses": json.loads(row["weaknesses"]) if row["weaknesses"] else {},
                "skills": json.loads(row["identified_skills"]) if row["identified_skills"] else {},
                "suggestions": json.loads(row["recommended_skills"]) if row["recommended_skills"] else {},
                "scores": json.loads(row["analysis_scores"]) if row["analysis_scores"] else {},
                "timestamp": row["analysis_timestamp"]
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving analysis: {e}")
        return None
    finally:
        conn.close()

if __name__ == '__main__':
    create_tables()
    print("Database tables created successfully.")
