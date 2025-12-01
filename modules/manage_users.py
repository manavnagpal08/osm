import streamlit as st
from firebase_admin import firestore

db = st.session_state.db

st.title("👤 Manage Users")

username = st.text_input("New Username")
password = st.text_input("Password", type="password")
role = st.selectbox("Select Role", ["design", "printing", "diecut", "assembly", "packaging", "admin"])

if st.button("Create User"):
    if username and password:
        db.collection("users").document(username).set({
            "username": username,
            "password": password,
            "role": role
        })
        st.success(f"User {username} created successfully!")
    else:
        st.error("Fill all fields")
