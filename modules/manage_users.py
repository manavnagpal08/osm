import streamlit as st
from firebase import read, push, update  # your REST-based Firebase wrapper

st.title("👤 User Management (Admin Only)")

st.subheader("Create New User")

username = st.text_input("Username")
password = st.text_input("Password", type="password")
role = st.selectbox("Role", [
    "admin",
    "design",
    "printing",
    "diecut",
    "assembly",
    "packaging",
])

if st.button("Create User"):
    if username.strip() == "" or password.strip() == "":
        st.error("Please enter username and password")
    else:
        data = {
            "username": username,
            "password": password,
            "role": role
        }
        # save to Firestore
        update("users", username, data)   # update() replaces or creates document
        st.success(f"User '{username}' created successfully!")
