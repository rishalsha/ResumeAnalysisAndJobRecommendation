import streamlit as st
from backend.auth import is_user_logged_in

def analysis_page():
    if not is_user_logged_in():
        st.error("You need to be logged in to access this page.")
        st.stop()
    st.title("Resume Analysis")
    st.write("This page is under construction.")
