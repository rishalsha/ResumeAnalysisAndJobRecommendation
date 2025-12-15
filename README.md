# Resume Analysis and Job Recommendation System

An intelligent application that analyzes user resumes and provides personalized job recommendations using LLM technology. Built with Streamlit for a seamless user experience.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the Application](#running-the-application)
- [Resume Analysis & Strengths/Weaknesses Analyzer](#resume-analysis--strengthsweaknesses-analyzer)
- [LLM Setup](#llm-setup)
- [Database Schema](#database-schema)
- [Contributing](#contributing)

## Features

✅ **User Authentication**: Secure registration and login with bcrypt password hashing
✅ **Resume Upload**: Support for PDF and DOCX file formats with validation
✅ **Text Extraction**: Automatic text extraction from resume files
✅ **Resume Analysis**: AI-powered analysis using Ollama LLM with strengths/weaknesses detection
✅ **Intelligent Caching**: Two-level cache (memory + disk) to avoid re-analyzing identical resumes
✅ **Confidence Scoring**: 0-100% confidence scores on all analyses
✅ **Database Storage**: Persistent storage of analysis results linked to user profiles
✅ **User Dashboard**: Central hub for navigation and quick stats
✅ **Profile Management**: User profile and settings pages
✅ **Job Recommendations**: Personalized job recommendations based on resume analysis

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

### Prerequisites: Start Ollama First

Ollama must be running before starting the Streamlit app. Open a terminal and run:

```bash
ollama serve --host localhost:11434
```

This starts the LLM service that powers the resume analysis features.

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

---

## Resume Analysis & Strengths/Weaknesses Analyzer

### Overview

AI-powered analyzer using Ollama LLM to identify resume strengths and weaknesses with detailed categorization, severity levels, and actionable recommendations.

### Analysis Types

#### **1. Strengths Analysis**

- Identifies 5-7 key strengths in order of importance
- Categories: formatting, content, skills, experience, education, achievements
- Importance levels: critical, high, medium
- Confidence scoring (0-100%)
- Specific examples from resume text

#### **2. Weaknesses Analysis**

- Identifies 5-7 key weaknesses
- Categories: formatting, content, skills, experience, missing_info, grammar, gaps
- Severity levels: critical, moderate, minor
- Location information (which section has the issue)
- Impact assessment on candidacy
- Specific fix recommendations

#### **3. Skills Extraction**

- Automatic detection of technical & soft skills
- Categorization by skill type
- JSON-structured output for integration

#### **4. Job Matching**

- Compare resume against job descriptions
- Match percentage calculation
- Gap analysis with recommendations

### Architecture

**Backend Components:**

1. **Enhanced LLMAnalyzer** (`backend/llm_analyzer.py`)

   - `AnalysisCache` class for intelligent caching with SHA-256 hashing
   - Specialized prompts for strength/weakness identification
   - Token tracking and retry logic with exponential backoff
   - Methods: `get_strengths()`, `get_weaknesses()`, `get_skills()`, `get_improvements()`, `match_job()`

2. **Database Integration** (`utils/database.py`)

   - `save_resume_analysis()` - Store analysis results with JSON serialization
   - `get_user_analysis()` - Retrieve user's latest analysis
   - Enhanced schema with strengths/weaknesses JSON fields

3. **Frontend Display** (`frontend/resume_analysis.py`)
   - Rich visual display with color-coded indicators
   - Support for all analysis types
   - Cache status indicator (⚡ badge)
   - Automatic database storage on completion

### Caching System

- **Two-level caching**: Memory (fast) + Disk (persistent)
- **SHA-256 hashing** for resume fingerprinting
- **~100x speedup** for re-analyzed resumes
- Automatic cache lookup before LLM calls

### Usage Example

1. Navigate to **Resume Analysis** in the dashboard
2. Select analysis type (Strengths, Weaknesses, etc.)
3. (Optional) Provide job description for job matching
4. Click analyze - results display with confidence scores
5. Results automatically saved to database and cached

---

## LLM Setup

### Environment Configuration (.env)

The application uses the following LLM configuration:

```env
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=60
LLM_MAX_RETRIES=3
```

### Supported Models

- **llama** (recommended) - 7B parameter model, good balance of speed/quality
- **mistral** - Faster alternative, good for quick analyses
- Custom models - Any Ollama-compatible model can be used

### Dependencies

All LLM integration packages are in `requirements.txt`:

- langchain
- langchain-community
- ollama
- requests
- python-dotenv

### Completed Features

✅ User authentication with bcrypt password hashing
✅ Resume upload & text extraction (PDF/DOCX)
✅ Resume analysis with AI-powered strengths & weaknesses detection
✅ Intelligent caching system for performance
✅ Database storage with JSON serialization
✅ User dashboard with navigation
✅ Profile management & settings pages
✅ Job recommendations engine
✅ Token tracking & retry logic

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
