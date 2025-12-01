import streamlit as st
import json
import time

# ----------------------------------------
# FIREBASE IMPORTS AND INITIALIZATION
# ----------------------------------------
# These imports are assumed to be available from the environment
try:
    from firebase import getFirestore, collection, doc, getDoc
except ImportError:
    st.error("Firebase SDK functions are missing. Please ensure your environment loads the Firebase modules correctly.")
    st.stop()

# Global variables provided by the environment (needed for collection path)
# The original JavaScript-style syntax is replaced with correct Python logic to access globals.
appId = locals().get('__app_id', 'default-app-id')
config_str = locals().get('__firebase_config', '{}')
try:
    firebaseConfig = json.loads(config_str)
except json.JSONDecodeError:
    st.error("Configuration error: Invalid Firebase config JSON.")
    st.stop()

# Define the common collection path helper
def get_users_collection():
    """Returns the reference to the public 'users' collection."""
    db = getFirestore()
    # Path: /artifacts/{appId}/public/data/users
    path = f"artifacts/{appId}/public/data/users"
    return collection(db, path)


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
    # WARNING: In a real app, this password must be securely hashed.
    "password": "admin123", 
    "role": "admin"
}

# ----------------------------------------
# FETCH USER (FIXED TO USE FIRESTORE SDK)
# ----------------------------------------
def get_user(username):
    # 1. Check if the requested user is the fallback default admin
    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN

    # 2. Try fetching from Firebase Firestore
    try:
        users_ref = get_users_collection()
        # Usernames are stored as the Document ID (as per manage_users.py)
        doc_ref = doc(users_ref, username)
        doc_snapshot = getDoc(doc_ref)

        if doc_snapshot.exists:
            return doc_snapshot.to_dict()
        
        return None # User not found in Firestore

    except Exception as e:
        st.error(f"Error reading user from database: {e}")
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
    input_username = username.strip()
    input_password = password.strip()
    
    if input_username == "" or input_password == "":
        st.error("Please enter both username and password.")
    else:
        user = get_user(input_username)

        if not user:
            st.error("User does not exist.")
        elif user.get("password") != input_password:
            st.error("Incorrect password.")
        else:
            # SUCCESS LOGIN
            st.session_state["username"] = input_username
            st.session_state["role"] = user.get("role")

            st.success("Login successful!")

            with open("app.py") as f:
                exec(f.read())
            st.stop()
