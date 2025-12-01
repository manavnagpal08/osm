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
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        button[kind="header"] {display:none !important;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='font-size:45px;'>🔐 Login to OMS</h1>", unsafe_allow_html=True)

    username = st.text_input("Username", key="username_input")
    password = st.text_input("Password", type="password", key="password_input")

    # 🔥 DEBUG 1 — See what widgets store
    st.write("DEBUG: raw username =", username)
    st.write("DEBUG: raw password =", password)

    if st.button("Login"):

        # 🔥 DEBUG 2 — Values inside button click
        st.write("DEBUG: inside button click, username =", username)
        st.write("DEBUG: inside button click, password =", password)

        username_clean = username.strip()
        password_clean = password.strip()

        # 🔥 DEBUG 3 — Cleaned values
        st.write("DEBUG: cleaned username =", username_clean)
        st.write("DEBUG: cleaned password =", password_clean)

        if not username_clean or not password_clean:
            st.error("Please enter both username and password.")
            # 🔥 DEBUG 4
            st.write("DEBUG: empty-check triggered!")
            return

        # 🔥 DEBUG 5 — before Firebase
        st.write("DEBUG: calling get_user() with", username_clean)

        user = get_user(username_clean)

        # 🔥 DEBUG 6 — result from Firebase
        st.write("DEBUG: user returned =", user)

        if not user:
            st.error("User not found.")
            st.write("DEBUG: USER NOT FOUND")
            return

        if user.get("password") != password_clean:
            st.error("Incorrect password.")
            st.write("DEBUG: PASSWORD MISMATCH")
            return

        # SUCCESS
        st.session_state["username"] = username_clean
        st.session_state["role"] = user["role"]

        st.success("Login successful!")

        # 🔥 DEBUG 7 — Show session_state
        st.write("DEBUG: session_state =", st.session_state)

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
    icon, file = menu[choice]
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
