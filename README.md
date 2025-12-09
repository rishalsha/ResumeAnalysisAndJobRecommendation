# Resume Analysis and Job Recommendation System

An intelligent application that analyzes user resumes and provides personalized job recommendations using LLM technology. Built with Streamlit for a seamless user experience.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Project Milestones](#project-milestones)
- [Database Schema](#database-schema)
- [Contributing](#contributing)

## Features

✅ **User Authentication**: Secure registration and login with bcrypt password hashing
✅ **Resume Upload**: Support for PDF and DOCX file formats with validation
✅ **Text Extraction**: Automatic text extraction from resume files
✅ **User Dashboard**: Central hub for navigation and quick stats
✅ **Profile Management**: User profile and settings pages
✅ **Job Recommendations**: Personalized job recommendations (in development)
✅ **Resume Analysis**: AI-powered resume analysis (in development)

## Project Structure

```
ResumeAnalysisAndJobRecommendationSystem/
├── app.py                          # Main Streamlit entry point
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── .env                           # Environment variables (not in git)
├── .gitignore                     # Git ignore rules
├── backend/
│   ├── __init__.py
│   ├── auth.py                    # Authentication & session management
│   └── resume_parser.py           # PDF/DOCX text extraction
├── frontend/
│   ├── __init__.py
│   ├── pages.py                   # Page routing configuration
│   ├── login.py                   # Login page
│   ├── registration.py            # Registration page
│   ├── dashboard.py               # Main dashboard
│   ├── profile.py                 # User profile page
│   ├── resume_analysis.py         # Resume analysis page
│   ├── job_recommendations.py     # Job recommendations page
│   └── settings.py                # User settings page
├── utils/
│   ├── __init__.py
│   └── database.py                # Database connection & CRUD operations
└── data/
    ├── database.db                # SQLite database
    └── resumes/                   # Uploaded resume files
```

## Setup & Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd ResumeAnalysisAndJobRecommendationSystem
```

### Step 2: Create a Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root directory:

```env
# Database configuration
DB_PATH=data/database.db

# API Keys (add as needed for future integrations)
# OPENAI_API_KEY=your_key_here
# LANGCHAIN_API_KEY=your_key_here
```

### Step 5: Initialize the Database

The database is automatically initialized when `utils/database.py` is imported. Tables are created on first run if they don't exist.

## Running the Application

### Start the Streamlit Server

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### Development Mode

For development with auto-reload:

```bash
streamlit run app.py --logger.level=debug
```

## Project Milestones

### MILESTONE 1: Foundation & User Registration (7 Tasks)

#### ✅ Task 1: Project Environment Setup

**Status**: COMPLETED

- [x] Python 3.9+ environment
- [x] Virtual environment created
- [x] All required libraries installed
- [x] Organized folder structure implemented
- [x] Git repository initialized
- [x] .gitignore file created
- [x] .env file support
- [x] README.md documentation

#### ✅ Task 2: Design Database Schema

**Status**: COMPLETED

- [x] SQLite database chosen for simplicity
- [x] Users schema implemented
  - user_id (Primary Key)
  - name, email (unique), password (hashed)
  - registration_date, resume_file_path
- [x] Resume Analysis schema implemented
  - analysis_id, user_id (Foreign Key)
  - extracted_text, analysis_scores, strengths, weaknesses
  - identified_skills, recommended_skills, analysis_timestamp
- [x] Job Recommendations schema implemented
  - job_id, user_id (Foreign Key)
  - job_title, company_name, location, job_description, job_url
  - match_percentage, scraping_date
- [x] Database utilities created (utils/database.py)
- [x] CRUD operations implemented
- [x] Proper indexing on user_id and email
- [x] Data validation rules

#### ✅ Task 3: Build User Registration Page (Frontend)

**Status**: COMPLETED

- [x] Registration form created (frontend/registration.py)
- [x] Input fields: Full Name, Email, Password, Confirm Password
- [x] Real-time input validation
  - Name: letters only, non-empty
  - Email: proper format with regex
  - Password: 8+ chars, uppercase, lowercase, number, special char
  - Confirm Password: must match
- [x] Error messages displayed
- [x] Register button functionality
- [x] Link to login page

#### ✅ Task 4: Implement User Authentication Backend

**Status**: COMPLETED

- [x] Authentication module (backend/auth.py)
- [x] Registration function with:
  - Email duplicate check
  - bcrypt password hashing
  - User data storage
- [x] Login function with:
  - User retrieval by email
  - Password verification with bcrypt
  - Session creation
- [x] Session management using st.session_state
- [x] Helper functions (is_user_logged_in, logout_user, get_current_user_name)
- [x] Error handling for database and validation

#### ✅ Task 5: Build Resume Upload Interface (Frontend)

**Status**: COMPLETED

- [x] Resume upload section in dashboard
- [x] File uploader (PDF and DOCX only)
- [x] File validation:
  - Size limit: 5MB
  - Extensions: .pdf, .docx only
  - File corruption check
- [x] Upload progress indicator
- [x] Success message display
- [x] File details preview (name, size)
- [x] Unique file naming (user_id + timestamp)
- [x] File storage in data/resumes/

#### ✅ Task 6: Implement Resume Text Extraction (Backend)

**Status**: COMPLETED

- [x] Resume parser module (backend/resume_parser.py)
- [x] PDF text extraction with PyPDF2
- [x] DOCX text extraction with python-docx
- [x] Unified extraction function
- [x] Text cleaning (whitespace, special characters)
- [x] Error handling (corrupted files, password-protected PDFs)
- [x] Database storage of extracted text
- [x] Logging for tracking operations

#### ✅ Task 7: Create User Dashboard (Frontend)

**Status**: COMPLETED

- [x] Main dashboard page (frontend/dashboard.py)
- [x] Welcome header with username
- [x] Navigation menu (sidebar)
- [x] Quick stats section:
  - Resume upload status
  - Last analysis date
  - Job recommendations count
- [x] Session state management
- [x] Login check and redirect
- [x] Navigation to other pages
- [x] Call-to-action buttons

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resume_file_path TEXT
)
```

### Resume Analysis Table

```sql
CREATE TABLE resume_analysis (
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
```

### Job Recommendations Table

```sql
CREATE TABLE job_recommendations (
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
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Submit a pull request with a clear description

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For issues or questions, please open an issue on the GitHub repository.
