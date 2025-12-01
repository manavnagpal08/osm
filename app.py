import streamlit as st
import os
from firebase import read

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
# LOAD MODULE PAGE
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
# NEW BEAUTIFUL LOGIN PAGE (STYLE 5)
# ---------------------------------------------------------
def login_screen():

    st.markdown("""
    <style>
        /* Hide Sidebar */
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}

        /* Background Image */
        body {
            background-image: url('https://images.unsplash.com/photo-1520880867055-1e30d1cb001c');
            background-size: cover;
            background-position: center;
        }

        /* Centered Login Card */
        .login-container {
            backdrop-filter: blur(12px);
            background: rgba(255,255,255,0.18);
            padding: 40px;
            border-radius: 16px;
            width: 380px;
            margin: auto;
            margin-top: 140px;
            box-shadow: 0 4px 40px rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.3);
        }

        .login-title {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            color: white;
            margin-bottom: 25px;
        }

        label, input {
            color: white !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    # 100% Reliable login button
    if st.button("Login", key="login_btn"):
        username_clean = username.strip()
        password_clean = password.strip()

        if not username_clean or not password_clean:
            st.error("Please enter both fields.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        user = get_user(username_clean)

        if not user:
            st.error("User not found.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        if user.get("password") != password_clean:
            st.error("Incorrect password.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        st.session_state.username = username_clean
        st.session_state.role = user["role"]

        st.success("Login successful!")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


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
# DEPARTMENT ROUTER
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

# After Login
st.title("📦 OMS Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {st.session_state['role']}")

if st.session_state["role"] == "admin":
    admin_sidebar()
else:
    department_router()
