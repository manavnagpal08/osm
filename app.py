import streamlit as st
import os
from firebase import read, update

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
    fb_user = read(f"users/{username}")

    if isinstance(fb_user, dict):
        return fb_user

    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN

    return None


# ---------------------------------------------------------
# PAGE LOADER FOR MODULES
# ---------------------------------------------------------
def load_page(page_file):
    full_path = os.path.join("modules", page_file)
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            code = compile(f.read(), full_path, "exec")
            exec(code, globals())
    else:
        st.error(f"Page not found: {page_file}")


# ---------------------------------------------------------
# LOGIN SCREEN
# ---------------------------------------------------------


def login_screen():

    # --- RESET LOGIN BUTTON ON FIRST PAGE LOAD ---
    if "login_button_triggered" not in st.session_state:
        st.session_state.login_button_fix = False
        st.session_state.login_button_triggered = True

    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='font-size:45px;'>🔐 Login to OMS</h1>", unsafe_allow_html=True)

    username = st.text_input("Username", key="login_username_field")
    password = st.text_input("Password", type="password", key="login_password_field")

    clicked = st.button("Login", key="login_button_fixed")

    # --------- FIX: Prevent FIRST false click ---------
    if not st.session_state.get("login_button_fix") and clicked:
        st.session_state.login_button_fix = True
        st.rerun()

    # After rerun, process normally
    if clicked:
        username_clean = username.strip()
        password_clean = password.strip()

        if not username_clean or not password_clean:
            st.error("Please enter both username and password.")
            return

        user = get_user(username_clean)

        if not user:
            st.error("User not found.")
            return

        if user.get("password") != password_clean:
            st.error("Incorrect password.")
            return

        st.session_state.username = username_clean
        st.session_state.role = user["role"]

        st.success("Login successful!")
        st.rerun()


# ---------------------------------------------------------
# SIDEBAR FOR ADMIN
# ---------------------------------------------------------
def admin_sidebar():
    st.sidebar.markdown("### 🧭 Navigation")

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
    _, file = menu[choice]
    load_page(file)


# ---------------------------------------------------------
# NON-ADMIN AUTO PAGE ROUTE
# ---------------------------------------------------------
def department_router():
    role = st.session_state["role"]

    page_map = {
        "design": "create_order.py",
        "printing": "printing.py",
        "diecut": "diecut.py",
        "assembly": "assembly.py",
        "packaging": "packaging.py",
    }

    file = page_map.get(role)
    if file:
        load_page(file)
    else:
        st.error("No page assigned to your role.")


# ---------------------------------------------------------
# APP ENTRY POINT
# ---------------------------------------------------------
if "role" not in st.session_state:
    login_screen()
    st.stop()

# LOGGED IN HEADER
st.title("📦 OMS Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {st.session_state['role']}")

if st.session_state["role"] == "admin":
    admin_sidebar()
else:
    department_router()
