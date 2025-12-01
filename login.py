import streamlit as st
from firebase import read  # your REST Firebase wrapper

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

# ----------------------------------------------------------
# DEFAULT ADMIN USER (ALWAYS AVAILABLE)
# You may modify this:
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}
# ----------------------------------------------------------


# ----------------------------------------
# FETCH USER FROM FIREBASE
# ----------------------------------------
def get_user(username):
    """
    Fetch a user from Firestore.
    If not found and username==admin → use default admin.
    """
    # Try Firebase first
    doc = read("users", username)
    if doc:
        return doc
    
    # Fallback to built-in admin
    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN

    return None


# ----------------------------------------
# IF ALREADY LOGGED IN → LOAD DASHBOARD
# ----------------------------------------
if "role" in st.session_state:
    with open("app.py", "r") as f:
        exec(f.read())
    st.stop()


# ----------------------------------------
# LOGIN FORM
# ----------------------------------------
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):

    if not username or not password:
        st.error("Please enter both fields.")
        st.stop()

    user = get_user(username)

    if not user:
        st.error("User not found.")
        st.stop()

    if password != user.get("password"):
        st.error("Incorrect password.")
        st.stop()

    # LOGIN SUCCESS
    st.session_state["username"] = username
    st.session_state["role"] = user.get("role")

    st.success("Login successful!")

    with open("app.py", "r") as f:
        exec(f.read())
    st.stop()
