from xmlrpc.client import FastParser

import streamlit as st
import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from utils import validate as vd

name = st.text_input("Full Name")
name = " ".join(word.capitalize() for word in name.split())

if not name:
        st.write("Name must not be empty!")
        isValidName = False
elif not name.replace(" " ,"").isalpha() :
    st.write("Name should only contain alphabets!")
    isValidName = False
else:
    isValidName =True

mail_id= st.text_input("Email Id")
isValidMail = vd.validate_email(mail_id)
if not isValidMail :
    if mail_id=="":
        st.write("Email must not be empty!")
    else:
        st.write("Invalid email id!")

password = st.text_input(type="password" , label="Password")
isValidPassword = vd.validate_password(password)
st.write(isValidPassword[1])


if st.button("Register"):
    if isValidPassword and isValidMail and isValidName :
        st.text("Registration success!")
        st.text(f"Welcome {name},")
    else:
        st.text("Registration failed!")
