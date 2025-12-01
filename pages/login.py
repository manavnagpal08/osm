import streamlit as st

st.set_page_config(page_title="OMS Login", layout="centered")

# ---------------------------
# HIDE SIDEBAR ON LOGIN PAGE
# ---------------------------
hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

st.title("🔐 Login to OMS")

# ---------------------------
# HARDCODED USER DATABASE
# ---------------------------
USERS = {
    "admin2": {"password": "admin123", "role": "admin"},
    "design01": {"password": "design123", "role": "design"},
    "print02": {"password": "print123", "role": "printing"},
    "die01": {"password": "die123", "role": "diecut"},
    "assembly01": {"password": "assembly123", "role": "assembly"},
    "dispatch01": {"password": "dispatch123", "role": "dispatch"},
}

# If already logged in → go dashboard
if "role" in st.session_state:
    st.switch_page("app.py")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if username in USERS and USERS[username]["password"] == password:
        st.session_state["username"] = username
        st.session_state["role"] = USERS[username]["role"]
        st.success("Login successful!")
        st.switch_page("app.py")
    else:
        st.error("Invalid username or password")
