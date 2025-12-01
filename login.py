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
# DEFAULT ADMIN USER
# ----------------------------------------
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}

# ----------------------------------------
# FETCH USER
# ----------------------------------------
def get_user(username):
    # Try Firebase
    doc = read("users", username)
    if doc:
        return doc

    # Fallback admin
    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN

    return None

# ----------------------------------------
# IF ALREADY LOGGED IN
# ----------------------------------------
if "role" in st.session_state:
    with open("app.py") as f:
        exec(f.read())
    st.stop()


# ----------------------------------------
# LOGIN FORM
# ----------------------------------------
username = st.text_input("Username", value="", key="username_input")
password = st.text_input("Password", type="password", value="", key="password_input")

if st.button("Login"):
    # FIX: strip spaces and check properly
    if username.strip() == "" or password.strip() == "":
        st.error("Please enter both username and password.")
    else:
        user = get_user(username.strip())

        if not user:
            st.error("User does not exist.")
        elif user.get("password") != password.strip():
            st.error("Incorrect password.")
        else:
            # SUCCESS LOGIN
            st.session_state["username"] = username.strip()
            st.session_state["role"] = user.get("role")

            st.success("Login successful!")

            with open("app.py") as f:
                exec(f.read())
            st.stop()
