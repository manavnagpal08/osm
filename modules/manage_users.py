import streamlit as st
from firebase import update

st.title("👤 User Management")

username = st.text_input("New Username")
password = st.text_input("Password", type="password")
role = st.selectbox("Select Role", [
    "admin",
    "design",
    "printing",
    "diecut",
    "assembly",
    "packaging",
])

if st.button("Create User"):
    if username.strip() == "" or password.strip() == "":
        st.error("Please fill all fields.")
    else:
        data = {
            "username": username,
            "password": password,
            "role": role
        }
        update(f"users/{username}", data)
        st.success(f"User '{username}' created successfully!")
