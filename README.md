<<<<<<< HEAD
# Project Setup

This document details the step-by-step process of setting up the project environment.

## 1. Dependency Management

First, a `requirements.txt` file was created to manage the project's Python dependencies.

**`requirements.txt`:**
```
streamlit
langchain
selenium
PyPDF2
python-docx
bcrypt
pymongo
```

With the `requirements.txt` file in place, the dependencies were installed into the project's virtual environment using the following command:

```bash
pip install -r requirements.txt
```

## 2. Project Structure

A well-organized folder structure was created to separate the different parts of the application.

```
.
├── backend/
├── data/
├── frontend/
└── utils/
```

- **`backend/`**: This directory will contain the backend logic, including database models and business logic.
- **`data/`**: This directory is for data storage, such as uploaded files and scraped content.
- **`frontend/`**: This directory will hold the Streamlit pages for the UI.
- **`utils/`**: This directory is for utility functions and helper scripts.

## 3. Version Control

A Git repository was initialized to track changes to the project.

```bash
git init
```

A `.gitignore` file was also created to prevent sensitive information and unnecessary files from being committed to the repository.

**`.gitignore`:**
```
# Virtual Environment
.venv/
__pycache__/
*.pyc

# IDE
.idea/

# Environment variables
.env

# Data files
data/

# Logs
*.log
```

## 4. Environment Variables

A `.env` file was created to store sensitive credentials, such as API keys. This file is included in the `.gitignore` to prevent it from being committed to the repository.

## Next Steps

The project is now set up and ready for development. The next steps will involve developing the application's features, starting with the main application entry point in `main.py`.
=======
# ResumeAnalysisAndJobRecommendation
>>>>>>> 14de0594813cddeb4aae4a51f00148a02de0affc
