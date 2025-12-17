import streamlit as st
import bcrypt
from utils.database import get_user_by_email, create_user as db_create_user

def register_user(name, email, password):

    if get_user_by_email(email):
        return False, "Email already registered."

    user_id = db_create_user(name, email, password)
    if user_id:
        return True, "Registration successful!"
    else:
        return False, "An error occurred during registration."

def login_user(email, password):
    """
    Logs in a user.
    Returns (success, message).
    """
    user = get_user_by_email(email)
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user['id']
        st.session_state['user_name'] = user['name']
        return True, "Login successful!"
    else:
        return False, "Invalid email or password."

def is_user_logged_in():
    return 'logged_in' in st.session_state and st.session_state['logged_in']

def logout_user():
    """Logs out the current user."""
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'user_name' in st.session_state:
        del st.session_state['user_name']

def get_current_user_name():
    """Returns the name of the currently logged-in user."""
    if is_user_logged_in():
        return st.session_state['user_name']
    return None

def get_logged_in_user_id():
    """Returns the ID of the currently logged-in user."""
    if is_user_logged_in():
        return st.session_state.get('user_id')
    return None
