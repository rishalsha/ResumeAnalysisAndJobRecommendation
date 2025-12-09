import streamlit as st
from frontend.pages import LOGGED_IN_PAGES
from backend.auth import is_user_logged_in, logout_user
from frontend import login, registration

# Ensure database tables and data directories exist on startup
from utils.database import create_tables

# Initialize DB and required directories (idempotent)
create_tables()


def main():
    st.sidebar.title("Navigation")

    if 'page' not in st.session_state:
        st.session_state['page'] = 'Login' if not is_user_logged_in() else 'Dashboard'

    if is_user_logged_in():
        pages = LOGGED_IN_PAGES
        if st.sidebar.button("Logout"):
            logout_user()
            st.session_state['page'] = 'Login'
            st.rerun()
        
        # Get the index of the current page
        page_names = list(pages.keys())
        try:
            index = page_names.index(st.session_state['page'])
        except ValueError:
            index = 0

        selection = st.sidebar.radio("Go to", page_names, key="navigation", index=index)
    
    else:
        pages = {
            "Login": login.login_page,
            "Registration": registration.registration_page
        }
        selection = st.sidebar.radio("Go to", list(pages.keys()), key="navigation")

    st.session_state['page'] = selection

    pages[selection]()

if __name__ == "__main__":
    main()
