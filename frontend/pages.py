from frontend import dashboard, profile, resume_analysis, job_recommendations, settings, showdatabase


LOGGED_IN_PAGES = {
    "Dashboard": dashboard.dashboard_page,
    "My Profile": profile.profile_page,
    "Resume Analysis": resume_analysis.analysis_page,
    "Job Recommendations": job_recommendations.recommendations_page,
    "Database Status": showdatabase.database_status_page,
    "Settings": settings.settings_page,
}

# Pages accessible when the user is not logged in
LOGGED_OUT_PAGES = {
    "Login": "frontend.login.login_page",
    "Registration": "frontend.registration.registration_page",
}
