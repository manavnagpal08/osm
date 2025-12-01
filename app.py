import streamlit as st
import os
from firebase import read, update  # Assuming these custom functions are available

# --- DEBUG: Start of App ---
st.write("--- DEBUG: APP START ---")

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(page_title="OMS System", layout="wide")


# ---------------------------------------------------------
# DEFAULT ADMIN USER
# ---------------------------------------------------------
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}


# ---------------------------------------------------------
# GET USER FROM FIREBASE
# ---------------------------------------------------------
def get_user(username):
    # --- DEBUG: get_user called ---
    st.write(f"DEBUG: get_user called for username: {username}")
    
    # NOTE: This uses custom 'read' function. If your 'login.py' uses Firestore SDK, 
    # there is a system-wide path mismatch here which may cause errors.
    fb_user = read(f"users/{username}")

    st.write(f"DEBUG: Firebase read result type: {type(fb_user)}")

    if isinstance(fb_user, dict):
        st.write(f"DEBUG: User found in Firebase with role: {fb_user.get('role')}")
        return fb_user

    if username == DEFAULT_ADMIN["username"]:
        st.write("DEBUG: Using DEFAULT_ADMIN fallback.")
        return DEFAULT_ADMIN

    st.write("DEBUG: User not found in Firebase or as default admin.")
    return None


# ---------------------------------------------------------
# PAGE LOADER FOR MODULES
# ---------------------------------------------------------
def load_page(page_file):
    full_path = os.path.join("modules", page_file)
    st.write(f"DEBUG: Attempting to load module from path: {full_path}")
    
    if os.path.exists(full_path):
        try:
            with open(full_path, "r") as f:
                code = compile(f.read(), full_path, "exec")
                exec(code, globals())
            st.write(f"DEBUG: Successfully loaded module: {page_file}")
        except Exception as e:
            st.error(f"Error executing page {page_file}: {e}")
            st.write(f"DEBUG: Error during module execution: {e}")
    else:
        st.error(f"Page not found: {page_file}")
        st.write(f"DEBUG: Module file not found: {full_path}")


# ---------------------------------------------------------
# LOGIN SCREEN
# ---------------------------------------------------------
def login_screen():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        button[kind="header"] {display:none !important;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='font-size:45px;'>🔐 Login to OMS</h1>", unsafe_allow_html=True)

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        username = username.strip()
        password = password.strip()
        
        st.write(f"DEBUG: Login button clicked. Input Username: {username}")

        if not username or not password:
            st.error("Please enter both username and password.")
            return

        user = get_user(username)

        if not user:
            st.error("User not found.")
            st.write("DEBUG: Login failed: User not found.")
            return

        if user.get("password") != password:
            st.error("Incorrect password.")
            st.write("DEBUG: Login failed: Password mismatch.")
            return

        # SUCCESS LOGIN
        st.session_state["username"] = username
        st.session_state["role"] = user["role"]
        
        st.write(f"DEBUG: Login successful! Role set to: {st.session_state['role']}")
        st.rerun()


# ---------------------------------------------------------
# SIDEBAR FOR ADMIN
# ---------------------------------------------------------
def admin_sidebar():
    st.sidebar.markdown("### 🧭 Navigation")
    st.write("DEBUG: Admin sidebar activated.")

    menu = {
        "Create Order": ("📦", "create_order.py"),
        "Design Dept": ("🎨", "design.py"),
        "Printing Dept": ("🖨️", "printing.py"),
        "Die-Cut Dept": ("✂️", "diecut.py"),
        "Assembly Dept": ("🔧", "assembly.py"),
        "Packaging Dept": ("📦✨", "packaging.py"),
        "All Orders": ("📋", "all_orders.py"),
        "User Management": ("🧑‍💼", "manage_users.py"),
    }

    if "menu_choice" not in st.session_state:
        st.session_state.menu_choice = "Create Order"

    choice = st.sidebar.radio(
        "Select Page",
        list(menu.keys()),
        index=list(menu.keys()).index(st.session_state.menu_choice)
    )

    st.session_state.menu_choice = choice
    icon, file = menu[choice]
    
    st.write(f"DEBUG: Admin sidebar selected choice: {choice}. File: {file}")
    load_page(file)


# ---------------------------------------------------------
# NON-ADMIN AUTO PAGE ROUTE
# ---------------------------------------------------------
def department_router():
    role = st.session_state["role"]
    st.write(f"DEBUG: Department router activated for role: {role}")

    page_map = {
        # Note: I've updated 'design' to 'design.py' for consistency with the admin menu.
        "design": "design.py",
        "printing": "printing.py",
        "diecut": "diecut.py",
        "assembly": "assembly.py",
        "packaging": "packaging.py",
    }

    file = page_map.get(role)
    
    st.write(f"DEBUG: Department page file determined: {file}")

    if file:
        load_page(file)
    else:
        st.error("No page assigned to your role.")


# ---------------------------------------------------------
# APP ENTRY POINT
# ---------------------------------------------------------
st.write(f"DEBUG: Checking session state for 'role': {'role' in st.session_state}")

if "role" not in st.session_state:
    st.write("DEBUG: Role not found. Calling login screen.")
    login_screen()
    st.stop()

# LOGGED IN HEADER
st.title("📦 OMS Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {st.session_state['role']}")

st.write(f"DEBUG: User is logged in. Routing based on role: {st.session_state['role']}")

if st.session_state["role"] == "admin":
    admin_sidebar()
else:
    department_router()
    
st.write("--- DEBUG: APP END ---")
