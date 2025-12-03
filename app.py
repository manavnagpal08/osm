import streamlit as st 
import os
from firebase import read, update
import streamlit.components.v1 as components

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="OMS System", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

# --------------------------------------------------------
# 🔔 ROUTE: Receive FCM token
# --------------------------------------------------------
try:
    params = st.experimental_get_query_params()
    if "upload_admin_token" in params:
        raw = st.request.body.decode()
        update("admin_tokens", {"token": raw})
        st.write("Token saved")
        st.stop()
except:
    pass


# ------------------ CONSTANTS ---------------------
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}

DEPARTMENT_PAGE_MAP = {
    "design": "design.py",
    "printing": "printing.py",
    "lamination": "lamination.py",
    "diecut": "diecut.py",
    "assembly": "assembly.py",
    "packaging": "packaging.py",
}

# ------------------ UTILITY FUNCTIONS ---------------------

def get_user(username):
    try:
        fb_user = read(f"users/{username}") 
        if isinstance(fb_user, dict) and "password" in fb_user:
            return fb_user
    except:
        pass

    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN
    
    return None


def load_page(page_file):
    if not page_file.endswith(".py"):
        st.error("Invalid page module!")
        return

    full_path = os.path.join("modules", page_file)
    
    if os.path.exists(full_path):
        try:
            exec(open(full_path, "r").read(), globals())
        except Exception as e:
            st.error(f"Error in {page_file}: {e}")
    else:
        st.error(f"Page not found: {page_file}")


def logout():
    for key in list(st.session_state.keys()):
        if key != "theme":
            del st.session_state[key]
    st.rerun()


# ------------------ GLOBAL CSS (with mobile collapsible sidebar) ---------------------

def inject_global_css():
    st.markdown("""
    <style>

    /* Hide Streamlit top bar */
    [data-testid="stHeader"] { display: none !important; }

    .stApp { font-family: 'Poppins', sans-serif; }

    /* Desktop Sidebar */
    [data-testid="stSidebar"] {
        background: #1f2833;
        color: white;
        width: 250px !important;
        min-width: 250px !important;
        box-shadow: 4px 0px 20px rgba(0,0,0,0.5);
    }

    .sidebar-header {
        padding: 25px 10px;
        color: white;
        font-size: 22px;
        text-align: center;
        font-weight: 700;
        border-bottom: 1px solid #444;
    }

    /* ------------------------------------------------------------ */
    /* 📱 Mobile Collapsible Sidebar */
    /* ------------------------------------------------------------ */

    @media (max-width: 768px) {

        /* Hide sidebar initially */
        [data-testid="stSidebar"] {
            transform: translateX(-260px);
            transition: 0.35s;
            position: fixed !important;
            z-index: 15000 !important;
            top: 0;
            left: 0;
            bottom: 0;
        }

        /* Slide-in when open */
        body.sidebar-open [data-testid="stSidebar"] {
            transform: translateX(0);
        }

        /* Push content right when sidebar opens */
        body.sidebar-open .stMain {
            margin-left: 240px !important;
            transition: 0.35s;
        }
    }

    /* Login box */
    .login-container {
        padding: 40px;
        width: 380px;
        margin: auto;
        margin-top: 150px;
        background: rgba(255,255,255,0.9);
        border-radius: 12px;
        box-shadow: 0px 4px 25px rgba(0,0,0,0.3);
    }

    .login-title {
        font-size: 26px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 20px;
    }

    </style>
    """, unsafe_allow_html=True)

# ------------------ LOGIN SCREEN ---------------------

def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            btn = st.form_submit_button("Login")

            if btn:
                user = get_user(username)

                if not user:
                    st.error("User not found.")
                    return
                if user["password"] != password:
                    st.error("Incorrect password.")
                    return

                st.session_state.username = username
                st.session_state.role = user["role"]
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# ------------------ ADMIN SIDEBAR ---------------------

def admin_sidebar():

    st.sidebar.markdown('<div class="sidebar-header">📦 OMS Admin</div>', unsafe_allow_html=True)

    MENU = {
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

    choice = st.sidebar.radio("Navigation", list(MENU.keys()))

    load_page(MENU[choice])

    st.sidebar.button("Logout", on_click=logout)


# ------------------ DEPARTMENT ROUTER ---------------------

def department_router():
    role = st.session_state["role"]

    st.markdown(f"## ⚙️ {role.title()} Department")
    st.button("Logout", on_click=logout)

    load_page(DEPARTMENT_PAGE_MAP.get(role, ""))


# ------------------ MAIN APP ---------------------

def main_app():
    st.markdown("## 📦 OMS Management System")
    st.caption(f"Logged in as **{st.session_state['username']}** — Role: **{st.session_state['role']}**")
    st.markdown("---")

    if st.session_state["role"] == "admin":
        admin_sidebar()
    else:
        department_router()


# ------------------ EXECUTION STARTS HERE ---------------------

inject_global_css()

# ------------------ WORKING CLICKABLE HAMBURGER ------------------

components.html("""
    <div id="menu_btn"
         style="
            position: fixed;
            top: 15px;
            left: 15px;
            font-size: 30px;
            padding: 8px 14px;
            background: #1f2833;
            color: white;
            border-radius: 6px;
            z-index: 20000;
            cursor: pointer;
         ">
        ☰
    </div>

    <script>
        const btn = document.getElementById("menu_btn");
        btn.addEventListener("click", function() {
            document.body.classList.toggle("sidebar-open");
        });
    </script>
""", height=70)

# ------------------ LOGIN HANDLING ---------------------

if "role" not in st.session_state:
    login_screen()
    st.stop()

# ------------------ TOKEN ROUTE ---------------------

params = st.experimental_get_query_params()
if "upload_admin_token" in params and st.session_state["role"] == "admin":
    try:
        raw = st.request.body.decode()
        update("admin_tokens", {"token": raw})
        st.success("Token saved!")
    except Exception as e:
        st.error(str(e))
    st.stop()

# ------------------ START APP ---------------------
main_app()
