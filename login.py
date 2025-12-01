import streamlit as st
from firebase import read

st.set_page_config(page_title="OMS Login", layout="centered")

# ----------------------------------------
# HIDE SIDEBAR
# ----------------------------------------
st.markdown("""
<style>
    [data-testid="stSidebar"] {display:none !important;}
    [data-testid="collapsedControl"] {display:none !important;}
    button[kind="header"] {display:none !important;}
</style>
""", unsafe_allow_html=True)

st.title("🔐 Login to OMS")

# ----------------------------------------
# DEFAULT ADMIN USER (ALWAYS AVAILABLE)
# ----------------------------------------
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}

# ----------------------------------------
# GET USER FROM FIREBASE OR DEFAULT ADMIN
# ----------------------------------------
def get_user(username):
    # Correct Firebase path: "users/admin"
    fb_user = read(f"users/{username}")

    # If Firebase returns dict, use it
    if isinstance(fb_user, dict):
        return fb_user

    # If username matches fallback admin
    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN

    return None


# ----------------------------------------
# IF ALREADY LOGGED IN → LOAD DASHBOARD
# ----------------------------------------
if "role" in st.session_state:
    with open("app.py", "r") as f:
        exec(f.read(), globals())
    st.stop()


# ----------------------------------------
# LOGIN FORM
# ----------------------------------------
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):

    username = username.strip()
    password = password.strip()

    if not username or not password:
        st.error("Please enter both username and password.")
        st.stop()

    user = get_user(username)

    if not user:
        st.error("User not found.")
        st.stop()

    if user.get("password") != password:
        st.error("Incorrect password.")
        st.stop()

    # ----------------------------------------
    # SUCCESSFUL LOGIN
    # ----------------------------------------
    st.session_state["username"] = username
    st.session_state["role"] = user.get("role")

    st.success("Login successful!")

    with open("app.py", "r") as f:
        exec(f.read(), globals())
    st.stop()
