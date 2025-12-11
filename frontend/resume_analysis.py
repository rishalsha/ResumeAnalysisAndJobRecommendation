import streamlit as st

from backend.auth import is_user_logged_in
from backend.llm_analyzer import LLMAnalyzer
from utils.database import get_db_connection


def _get_user_resume_text_with_ts():
    """Fetch the user's most recent extracted resume text and its timestamp."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return "", None

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT extracted_text, analysis_timestamp
            FROM resume_analysis
            WHERE user_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT 1
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return "", None
        return row["extracted_text"], row["analysis_timestamp"]
    finally:
        conn.close()


def analysis_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    st.title("AI Resume Analysis")
    st.caption("Analyze your uploaded resume using AI (LangChain-enabled Ollama).")

    # Fetch user's resume from database - always fresh (with timestamp)
    resume_text, resume_ts = _get_user_resume_text_with_ts()
    
    if not resume_text:
        st.warning("❌ No resume found. Please upload a resume in the Dashboard first.")
        if st.button("Go to Dashboard to Upload"):
            st.session_state['page'] = 'Dashboard'
            st.rerun()
        st.stop()

    st.success("✅ Resume loaded and ready for analysis")

    # Refresh editable text if database content changed
    if (
        "resume_source_ts" not in st.session_state
        or st.session_state.get("resume_source_ts") != resume_ts
    ):
        st.session_state["resume_text"] = resume_text
        st.session_state["resume_source_ts"] = resume_ts

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Your Resume")
        st.session_state["resume_text"] = st.text_area(
            "Resume text (editable)",
            value=st.session_state.get("resume_text", ""),
            height=300,
        )

    with col2:
        st.subheader("Analysis Settings")
        
        analysis_type = st.selectbox(
            "Analysis type",
            [
                "Strengths",
                "Weaknesses",
                "Skills",
                "Suggestions",
                "Job Match",
                "Comprehensive",
            ],
        )

        job_description = ""
        if analysis_type == "Job Match":
            job_description = st.text_area(
                "Job description (required for Job Match)",
                height=200,
                placeholder="Paste the target job description here...",
            )

        with st.expander("Advanced", expanded=False):
            st.caption("Using Ollama via LangChain (from .env configuration).")
            st.caption("Temperature, timeouts, and retries are pre-configured.")

    run = st.button("Run Analysis", type="primary", use_container_width=True)

    if run:
        resume_text = st.session_state.get("resume_text", "").strip()
        if not resume_text:
            st.warning("Please provide resume text.")
            st.stop()

        if analysis_type == "Job Match" and not job_description.strip():
            st.warning("Please provide a job description for Job Match analysis.")
            st.stop()

        analyzer = LLMAnalyzer()

        with st.spinner("Contacting AI..."):
            conn = analyzer.test_connection()
            if conn.get("status") == "error":
                st.error(conn.get("message", "Connection failed."))
                st.stop()

            try:
                if analysis_type == "Strengths":
                    result = analyzer.get_strengths(resume_text)
                elif analysis_type == "Weaknesses":
                    result = analyzer.get_weaknesses(resume_text)
                elif analysis_type == "Skills":
                    result = analyzer.get_skills(resume_text)
                elif analysis_type == "Suggestions":
                    result = analyzer.get_improvements(resume_text)
                elif analysis_type == "Job Match":
                    result = analyzer.match_job(resume_text, job_description)
                else:
                    result = analyzer.comprehensive_analysis(resume_text)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

        st.subheader("Analysis Result")
        st.json(result)

        stats = analyzer.get_token_stats()
        st.caption(
            f"📊 Tokens used (approx): {stats.get('total_tokens', 0)} | Requests: {stats.get('requests_count', 0)}"
        )

