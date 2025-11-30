import streamlit as st
from firebase import read

st.set_page_config(page_title="OMS Login", layout="centered")

st.title("🔐 Login to OMS")

# If already logged in → go to app
if "role" in st.session_state:
    st.switch_page("app.py")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    users = read("users")

    if users and username in users:
        if users[username]["password"] == password:
            st.session_state["username"] = username
            st.session_state["role"] = users[username]["role"]

            st.success("Login successful!")
            st.switch_page("app.py")
        else:
            st.error("Incorrect password.")
    else:
        st.error("User does not exist.")
