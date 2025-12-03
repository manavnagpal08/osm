import streamlit as st 
import os
from firebase import read, update
import base64

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="OMS System", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

# --------------------------------------------------------
# 🔔 ROUTE: Receive FCM token from frontend (admin only)
# --------------------------------------------------------
try:
    params = st.experimental_get_query_params()
    if "upload_admin_token" in params:
        raw = st.request.body.decode()
        update("admin_tokens", {"token": raw})
        st.write("Token saved")
        st.stop()
except Exception:
    pass

# --- Constants ---
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}

# All departments
DEPARTMENT_PAGE_MAP = {
    "design": "design.py",
    "printing": "printing.py",
    "lamination": "lamination.py",
    "diecut": "diecut.py",
    "assembly": "assembly.py",
    "packaging": "packaging.py",
}

# --- Utility Functions ---


def get_user(username):
    """Retrieves user data from Firebase or returns the default admin."""
    try:
        fb_user = read(f"users/{username}") 
        if isinstance(fb_user, dict) and "password" in fb_user and "role" in fb_user:
            return fb_user
    except:
        pass 

    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN
    
    return None


def load_page(page_file):
    """Loads and executes a module from /modules folder."""
    if ".." in page_file or not page_file.endswith(".py"):
        st.error("Invalid page file request.")
        return

    full_path = os.path.join("modules", page_file)
    
    if os.path.exists(full_path):
        try:
            with open(full_path, "r") as f:
                code = compile(f.read(), full_path, "exec")
                exec(code, globals())
        except Exception as e:
            st.error(f"Error loading page {page_file}: {e}")
    else:
        st.error(f"Page not found: {page_file}")


def logout():
    """Clear session and return to login."""
    for key in list(st.session_state.keys()):
        if key not in ["theme"]:
            del st.session_state[key]
    st.rerun()


# --- GLOBAL CSS (Includes mobile collapsible sidebar) ---

def inject_global_css():
    st.markdown("""
    <style>

    /* GLOBAL FONT */
    .stApp {
        font-family: 'Poppins', sans-serif;
        background: white;
    }

    /* Hide Streamlit top header */
    [data-testid="stHeader"] {
        display: none !important;
    }

    /* --------------------------------------------- */
    /* LOGIN SCREEN STYLING */
    /* --------------------------------------------- */
    .login-container {
        backdrop-filter: blur(12px);
        background: rgba(255,255,255,0.18);
        padding: 40px;
        border-radius: 16px;
        width: 380px;
        margin: auto;
        margin-top: 140px;
        box-shadow: 0 4px 40px rgba(0,0,0,0.4);
        border: 1px solid rgba(255,255,255,0.3);
        text-align: left;
    }

    .login-title {
        color: #1f2833;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 20px;
        text-align: center;
    }

    /* --------------------------------------------- */
    /* DESKTOP SIDEBAR STYLING */
    /* --------------------------------------------- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1f2833 0%, #12181d 100%);
        box-shadow: 4px 0 25px rgba(0,0,0,0.6);
        width: 250px !important;
        min-width: 250px !important;
    }

    .sidebar-header {
        padding: 25px 15px 10px 15px;
        color: white;
        font-size: 24px;
        font-weight: 800;
        text-align: center;
        border-bottom: 2px solid;
        border-image: linear-gradient(to right, #00BFFF, #1E90FF) 1;
        margin-bottom: 25px;
    }

    /* --------------------------------------------- */
    /* 📱 MOBILE COLLAPSIBLE SIDEBAR SYSTEM */
    /* --------------------------------------------- */

    @media (max-width: 768px) {

        /* Hamburger Button */
        .mobile-menu-btn {
            position: fixed;
            top: 15px;
            left: 15px;
            font-size: 30px;
            padding: 8px 14px;
            background: #1f2833;
            color: white;
            border-radius: 6px;
            z-index: 20000 !important;
            cursor: pointer;
            display: block;
        }

        /* Hide sidebar initially */
        [data-testid="stSidebar"] {
            transform: translateX(-260px);
            transition: all 0.35s ease-in-out;
            position: fixed !important;
            left: 0;
            top: 0;
            bottom: 0;
            width: 240px !important;
            z-index: 15000 !important;
        }

        /* Sidebar open state */
        body.sidebar-open [data-testid="stSidebar"] {
            transform: translateX(0);
        }

        /* Push main content */
        body.sidebar-open .stMain {
            margin-left: 240px !important;
            transition: margin-left 0.35s ease-in-out;
        }
    }

    </style>
    """, unsafe_allow_html=True)




# --- LOGIN SCREEN ---

def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                    return

                user = get_user(username)

                if not user:
                    st.error("User not found.")
                    return

                if user.get("password") != password:
                    st.error("Incorrect password.")
                    return

                st.session_state.username = username
                st.session_state.role = user["role"]
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)



# --- ADMIN SIDEBAR NAVIGATION ---

def admin_sidebar():
    st.sidebar.markdown('<div class="sidebar-header">📦 OMS Admin</div>', unsafe_allow_html=True)

    ADMIN_MENU = {
        "Create Order": "create_order.py",
        "Design Dept": "design.py",
        "Printing Dept": "printing.py",
        "Lamination Dept": "lamination.py",
        "Die-Cut Dept": "diecut.py",
        "Assembly Dept": "assembly.py",
        "Packaging Dept": "packaging.py",
        "All Orders": "all_orders.py",
        "User Management": "manage_users.py",
    }

    if "admin_menu_choice" not in st.session_state:
        st.session_state.admin_menu_choice = "Create Order"

    choice = st.sidebar.radio("Navigation", list(ADMIN_MENU.keys()))

    if choice != st.session_state.admin_menu_choice:
        st.session_state.admin_menu_choice = choice
        st.rerun()

    load_page(ADMIN_MENU[choice])

    st.sidebar.button("Logout", on_click=logout)



# --- DEPARTMENT ROUTING ---

def department_router():
    role = st.session_state.get("role")
    
    st.markdown(f"## ⚙️ Welcome to the **{role.title()}** Department")
    st.button("Logout", on_click=logout)

    file = DEPARTMENT_PAGE_MAP.get(role)

    if file:
        load_page(file)
    else:
        st.error("Role not assigned.")



# --- MAIN APP ---

def main_app():
    st.markdown('<h1 style="color:#3498db;">📦 OMS Management System</h1>', unsafe_allow_html=True)
    st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")
    st.markdown("---")

    if st.session_state["role"] == "admin":
        admin_sidebar()
    else:
        department_router()



# --- EXECUTION FLOW ---

inject_global_css()

# Add Mobile Hamburger Button
st.markdown("""
    <div class="mobile-menu-btn" onclick="document.body.classList.toggle('sidebar-open');">
        ☰
    </div>
""", unsafe_allow_html=True)

# Login check
if "role" not in st.session_state:
    login_screen()
    st.stop()

# After login, check FCM secure route
params = st.experimental_get_query_params()
if "upload_admin_token" in params and st.session_state.get("role") == "admin":
    try:
        raw = st.request.body.decode()
        update("admin_tokens", {"token": raw})
        st.success("Admin device token saved!")
    except Exception as e:
        st.error(f"Error saving token: {e}")
    st.stop()

main_app()
