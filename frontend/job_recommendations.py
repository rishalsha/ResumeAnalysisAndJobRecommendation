import streamlit as st
from backend.auth import is_user_logged_in

def recommendations_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()
    st.title("Job Recommendations")
    st.write("This page is under construction.")
