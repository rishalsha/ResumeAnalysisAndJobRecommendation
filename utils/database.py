import sqlite3
import bcrypt
import os

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

if __name__ == '__main__':
    create_tables()
    print("Database tables created successfully.")
