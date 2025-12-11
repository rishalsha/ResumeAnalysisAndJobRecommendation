import streamlit as st
import os
import PyPDF2
import docx
import time
from backend.auth import is_user_logged_in, get_current_user_name
from utils.database import get_db_connection
from backend.resume_parser import parse_resume

MAX_FILE_SIZE = 5 * 1024 * 1024

def is_file_valid(file):

    if file.size > MAX_FILE_SIZE:
        return False, "File size exceeds the 5MB limit."

    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension not in ['.pdf', '.docx']:
        return False, "Invalid file format. Please upload a PDF or DOCX file."

    try:
        if file_extension == '.pdf':
            PyPDF2.PdfReader(file)
        elif file_extension == '.docx':
            docx.Document(file)
    except Exception:
        return False, "The file appears to be corrupted."

    return True, ""


def dashboard_page():

    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()

    # initialize uploader flag
    if 'show_resume_uploader' not in st.session_state:
        st.session_state['show_resume_uploader'] = False

    st.title(f"Welcome to your Dashboard, {get_current_user_name()}!")

    # Always refresh from database to ensure latest data
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = st.session_state['user_id']
    cursor.execute("SELECT resume_file_path FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT analysis_timestamp FROM resume_analysis WHERE user_id = ? ORDER BY analysis_timestamp DESC LIMIT 1", (user_id,))
    latest_analysis = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM job_recommendations WHERE user_id = ?", (user_id,))
    job_recommendation_count = cursor.fetchone()[0]
    conn.close()
    
    # Store in session to avoid multiple DB queries in same render
    st.session_state['user_resume_path'] = user['resume_file_path'] if user else None

    has_resume = bool(st.session_state.get('user_resume_path'))

    st.header("Quick Stats")
    col1, col2, col3 = st.columns(3)
    with col1:
        if has_resume:
            st.metric("Resume Status", "✅ Uploaded")
        else:
            st.markdown("**Resume Status**")
            st.markdown("<span style='font-size:14px'>❌ Not Uploaded</span>", unsafe_allow_html=True)
    with col2:
        st.metric("Last Analysis", latest_analysis['analysis_timestamp'].split(" ")[0] if latest_analysis else "Never")
    with col3:
        st.metric("Job Recommendations", job_recommendation_count)

    st.header("What would you like to do?")
    col1, col2 = st.columns(2)
    
    with col1:
        if not has_resume:
            if st.button("📤 Upload Your Resume"):
                st.session_state['show_resume_uploader'] = True
                st.rerun()
    with col2:
        if has_resume:
            if st.button("🔍 Analyze Your Resume"):
                st.session_state['page'] = 'Resume Analysis'
                st.rerun()


    with st.expander("Upload or Manage Your Resume", expanded=st.session_state.get('show_resume_uploader', False)):
        uploaded_file = st.file_uploader(
            "Choose a PDF or DOCX file",
            type=['pdf', 'docx'],
            accept_multiple_files=False
        )

        if uploaded_file is not None:
            is_valid, message = is_file_valid(uploaded_file)
            if not is_valid:
                st.error(message)
            else:
                st.write("File Details:")
                st.write(f"- **Name:** {uploaded_file.name}")
                st.write(f"- **Size:** {round(uploaded_file.size / 1024, 2)} KB")
                
                if st.button("Upload and Analyze Resume"):
                    with st.spinner("Uploading and parsing your resume..."):
                        file_extension = os.path.splitext(uploaded_file.name)[1]
                        unique_filename = f"{user_id}_{int(time.time())}{file_extension}"
                        file_path = os.path.join("data", "resumes", unique_filename)
                        
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Update the user's resume file path in the database
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET resume_file_path = ? WHERE id = ?", (file_path, user_id))
                        conn.commit()
                        conn.close()

                        # Update session immediately so UI reflects new state before rerun
                        st.session_state['user_resume_path'] = file_path

                        # Parse the resume and store the extracted text
                        parse_resume(file_path, user_id)

                    st.success("Resume uploaded and analyzed successfully!")
                    # collapse the uploader after successful upload
                    st.session_state['show_resume_uploader'] = False
                    st.rerun()

        if st.session_state.get('user_resume_path'):
            st.write(f"📄 Current resume: {os.path.basename(st.session_state['user_resume_path'])}")
            if st.button("🗑️ Delete Resume"):
                # Delete the file
                try:
                    if os.path.exists(st.session_state['user_resume_path']):
                        os.remove(st.session_state['user_resume_path'])
                except Exception as e:
                    st.warning(f"Could not delete file: {e}")
                
                # Update the database
                conn = get_db_connection()
                cursor = conn.cursor()
                # Also delete the analysis
                cursor.execute("DELETE FROM resume_analysis WHERE user_id = ?", (user_id,))
                cursor.execute("UPDATE users SET resume_file_path = NULL WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                
                st.session_state['user_resume_path'] = None
                st.success("Resume deleted successfully.")
                st.rerun()

    st.header("Recent Activity")
    st.write("This section is under construction.")
