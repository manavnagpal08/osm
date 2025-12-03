import streamlit as st
import os
# NOTE: Assuming 'firebase' module exists and provides read/update functions
from firebase import update, read 
import firebase_admin
from firebase_admin import credentials, db
import base64

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="OMS System", 
    layout="wide", 
    # Removed initial_sidebar_state="collapsed"
)
# --------------------------------------------------------
# 🔔 ROUTE: Receive FCM token from frontend (admin only) 
# --------------------------------------------------------
try:
    params = st.experimental_get_query_params()
    if "upload_admin_token" in params and st.request.method == 'POST':
        raw = st.request.body.decode()
        update("admin_tokens", {"token": raw})
        st.write("Token saved")
        st.stop()
except Exception as e:
    pass

# --- Constants ---
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

# --- Utility Functions ---

def get_user(username):
    """Retrieves user data from Firebase or returns the default admin."""
    try:
        fb_user = read(f"users/{username}") 
        if isinstance(fb_user, dict) and "password" in fb_user and "role" in fb_user:
            return fb_user
    except Exception:
        pass 
    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN
    return None

def load_page(page_file):
    """Dynamically loads and executes a page module from the 'modules' directory."""
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
            st.error(f"Error loading page **{page_file}** in modules folder: {e}")
    else:
        st.error(f"Page module not found: **{page_file}** (Expected in the 'modules/' folder)")

def logout():
    """Clears session state and reruns to show the login screen."""
    for key in list(st.session_state.keys()):
        if key not in ["theme"]: 
            del st.session_state[key]
    st.rerun()

# --- Custom CSS Injection ---

def inject_global_css():
    """Injects all global and local styles, optimized for Z-index, responsive design, and button clickability."""
    
    st.markdown("""
    <style>
        /* Global App Styling */
        .stApp {
            background-color: #FFFFFF; 
            font-family: 'Poppins', sans-serif;
        }

        /* ------------------------------------------------------------- */
        /* LOGIN SCREEN STYLING */
        /* ------------------------------------------------------------- */
        .stApp:has(.login-container) {
            background-image: url('https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh9JgbXkHFD_68MIoMrl8sOeanj-iPFaeHPB8IaMYuwcAsNAstm3ZYY9i33sPe4BKe-iwexUYISoCen0ZBSO8VV_JZG1R9Wszjv3yEyAL1BBZBn4xTarqdVloKEq9BLR6PNaBp47ao4ZdopDD3oVN1A0GIkNL0ijwB7R1eLKAYGv8LKht52gryczc57bUtS/s320/greb.png');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-color: transparent;
        }
        
        .stApp:has(.login-container) [data-testid="stHeader"], 
        .stApp:has(.login-container) [data-testid="stToolbar"], 
        .stApp:has(.login-container) [data-testid="stSidebar"],
        .stApp:has(.login-container) .mobile-menu-btn {
            display: none !important;
        }

        .stApp:not(:has(.login-container)) [data-testid="stHeader"] {
            display: none !important;
        }

        /* Login Card Styles (Keep as is) */
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
        
        /* ------------------------------------------------------------- */
        /* ADMIN SIDEBAR STYLING & Z-INDEX FIXES */
        /* ------------------------------------------------------------- */
        
        /* Sidebar Container: Applies to both desktop and mobile */
        .stApp:not(:has(.login-container)) [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1f2833 0%, #12181d 100%);
            box-shadow: 4px 0 25px rgba(0,0,0,0.7);
            width: 250px !important; 
            min-width: 250px !important; 
            transition: all 0.3s ease-in-out;
            z-index: 15000; 
            /* Use ABSOLUTE for better mobile control and FIXED for desktop */
            position: absolute; 
            height: 100vh;
        }
        
        /* ✅ FIX: Ensure sidebar content (buttons, radio) is clickable */
        [data-testid="stSidebar"] > div {
            z-index: 15001 !important; 
        }

        /* ------------------------------------------------------------- */
        /* 🖥️ DESKTOP ONLY FIXES (min-width: 769px) - Corrects Layout */
        /* ------------------------------------------------------------- */
        @media (min-width: 769px) {
             /* 1. Ensure the custom button is HIDDEN on desktop */
             .mobile-menu-btn {
                display: none !important; 
             }
             
             /* 2. ✅ FIX: Ensure sidebar is VISIBLE and FIXED on desktop */
             [data-testid="stSidebar"] {
                transform: translateX(0) !important;
                position: fixed !important; /* Fixed position for scrolling */
             }
             
             /* 3. ✅ FIX: Main content needs margin to avoid being covered by sidebar */
             .stMainBlockContainer {
                margin-left: 260px !important; 
             }
        }
        
        /* ------------------------------------------------------------- */
        /* 📱 MOBILE COLLAPSIBLE SIDEBAR (max-width: 768px) */
        /* ------------------------------------------------------------- */

        @media (max-width: 768px) {
            
            /* Hamburger button visible only on mobile (highest z-index) */
            .mobile-menu-btn {
                position: fixed;
                top: 15px;
                left: 15px;
                font-size: 28px;
                padding: 8px 14px;
                background: #1f2833;
                color: white;
                border-radius: 6px;
                z-index: 30000 !important; 
                cursor: pointer;
                display: block; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.5);
                line-height: 1;
            }

            /* 1. Initially HIDE sidebar on mobile */
            [data-testid="stSidebar"] {
                transform: translateX(-260px) !important;
                /* Position absolute on mobile to prevent full-screen scrolling issues */
                position: absolute !important; 
                top: 0;
                left: 0;
                height: 100vh;
                z-index: 20000 !important; 
            }

            /* 2. When open, move sidebar into view */
            body.sidebar-open [data-testid="stSidebar"] {
                transform: translateX(0) !important;
            }
            
            /* Mobile overlay: lower z-index than sidebar (20000) */
            body.sidebar-open .block-container::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5); 
                z-index: 10000; 
                pointer-events: auto; 
            }

            /* 3. Ensure main content starts at 0 on mobile */
            .stMainBlockContainer {
                margin-left: 0 !important;
            }
            
            /* Hide the default Streamlit hamburger on mobile */
            [data-testid="stSidebarToggleButton"] {
                display: none;
            }
        }
        
        /* --- General Sidebar Content Styling (Kept for Good Design) --- */
        .sidebar-header {
            padding: 25px 15px 10px 15px; 
            color: #f6f9fc;
            font-size: 24px; 
            font-weight: 800;
            text-align: center;
            border-bottom: 2px solid;
            border-image: linear-gradient(to right, #00BFFF, #1E90FF) 1;
            margin-bottom: 25px;
            text-shadow: 0 1px 3px rgba(0,0,0,0.5);
        }
        [data-testid="stSidebar"] .stRadio > div { padding: 0 5px; } 
        [data-testid="stSidebar"] .stRadio label * {
            color: #f6f9fc !important;
            text-shadow: 0 0 4px rgba(0, 0, 0, 0.4); 
        }
        [data-testid="stSidebar"] .stRadio label {
            padding: 12px 15px; 
            margin-bottom: 6px; 
            border-radius: 8px; 
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.2s ease-in-out; 
            font-weight: 500;
            font-size: 15px; 
        }
        [data-testid="stSidebar"] .stButton button {
            width: 90%;
            margin: 30px 5% 20px 5%;
            background-color: #1E90FF;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            padding: 12px;
            transition: all 0.2s;
        }
        
    </style>
    """, unsafe_allow_html=True)

# --- Login Screen ---

def login_screen():
    """Displays the login interface."""
    
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):

            username = st.text_input("Username", key="login_username_input", autocomplete="username")
            password = st.text_input("Password", type="password", key="login_password_input", autocomplete="current-password")

            submitted = st.form_submit_button("Login")

            if submitted:
                username_clean = username.strip()
                password_clean = password.strip()

                if not username_clean or not password_clean:
                    st.error("Please enter both username and password.")
                    return 

                user = get_user(username_clean)

                if not user or user.get("password") != password_clean:
                    st.error("Incorrect username or password.")
                    return

                st.session_state.username = username_clean
                st.session_state.role = user["role"]

                st.success("Login successful! Redirecting...")
                st.rerun() 

        st.markdown("</div>", unsafe_allow_html=True) 

# --- Admin Sidebar & Routing ---

def admin_sidebar():
    """Displays the navigation sidebar for 'admin' users."""
    
    st.sidebar.markdown('<div class="sidebar-header">📦 OMS Admin</div>', unsafe_allow_html=True)

    ADMIN_MENU = {
        "Create Order": ("📦", "create_order.py"),
        "Design Dept": ("🎨", "design.py"),
        "Printing Dept": ("🖨️", "printing.py"),
        "Lamination Dept": ("🛡️", "lamination.py"), 
        "Die-Cut Dept": ("✂️", "diecut.py"),
        "Assembly Dept": ("🔧", "assembly.py"),
        "Packaging Dept": ("📦✨", "packaging.py"),
        "All Orders": ("📋", "all_orders.py"),
        "User Management": ("🧑‍💼", "manage_users.py"),
    }

    if "admin_menu_choice" not in st.session_state:
        st.session_state.admin_menu_choice = "Create Order"

    display_options = [f"{icon} {key}" for key, (icon, file) in ADMIN_MENU.items()]
    
    current_key = st.session_state.admin_menu_choice
    current_index = list(ADMIN_MENU.keys()).index(current_key) if current_key in ADMIN_MENU else 0
    
    st.sidebar.markdown('<h3 style="color: #f6f9fc; padding: 0 15px;">🧭 Navigation</h3>', unsafe_allow_html=True)
    
    choice_with_icon = st.sidebar.radio(
        "", 
        display_options,
        index=current_index,
        key="admin_radio_menu" 
    )

    choice = " ".join(choice_with_icon.split(" ")[1:])

    if choice != st.session_state.admin_menu_choice:
          st.session_state.admin_menu_choice = choice
          st.rerun() 

    _, file = ADMIN_MENU[st.session_state.admin_menu_choice]
    load_page(file)
    
    st.sidebar.markdown("---")
    st.sidebar.button("Logout", on_click=logout) 


# --- Departmental Routing ---

def department_router():
    """Routes a non-admin user directly to their assigned department page."""
    
    role = st.session_state.get("role")
    
    st.markdown(f"## ⚙️ Welcome to the **{role.title()}** Department Portal")
    st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")
    st.markdown("---")

    col_btn, col_spacer = st.columns([0.2, 0.8])
    with col_btn:
        st.button("Logout", on_click=logout) 

    st.markdown("Please manage your assigned orders below.")

    file = DEPARTMENT_PAGE_MAP.get(role)

    if file:
        load_page(file)
    else:
        st.error(f"Your role **{role}** is not assigned to a department page.")

# --- Application Entry Point ---

def main_app():
    """Main function to handle post-login routing."""
    
    if st.session_state["role"] == "admin":
        
        st.markdown('<h1 style="color:#3498db;"><span>📦</span> OMS Management System</h1>', unsafe_allow_html=True)
        st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")
        st.markdown("---")
        
        admin_sidebar()
        
    elif st.session_state["role"] in DEPARTMENT_PAGE_MAP:
        department_router()
        
    else:
        st.error(f"Your role **{st.session_state['role']}** is not authorized to view any page. Please contact administration.")
        st.button("Logout", on_click=logout) 

# --- Main Execution Flow ---

# 🔥 Inject CSS styles first
inject_global_css()

# ---------------------------------------------------------
# 🚨 LOGIN ROUTING
# ---------------------------------------------------------

if "role" not in st.session_state:
    login_screen()
    st.stop()

# ---------------------------------------------------------
# ✅ Hamburger Button Injection (visible only on mobile)
# ---------------------------------------------------------

st.markdown("""
    <div class="mobile-menu-btn" onclick="
        document.body.classList.toggle('sidebar-open');
        let btn = this;
        // Optionally change icon from ☰ (&#9776;) to X (&times;)
        if (document.body.classList.contains('sidebar-open')) {
            btn.innerHTML = '&times;'; 
        } else {
            btn.innerHTML = '&#9776;';
        }
    ">
        &#9776; </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🔥 Secure FCM token handling (after login)
# ---------------------------------------------------------
params = st.experimental_get_query_params()
if "upload_admin_token" in params and st.session_state.get("role") == "admin":
    try:
        raw = st.request.body.decode()
        update("admin_tokens", {"token": raw})
        st.success("Admin device token saved!")
    except Exception as e:
        st.error(f"Error saving token or request body not found: {e}")
    st.stop()

# ---------------------------------------------------------
# 🚀 Run main application
# ---------------------------------------------------------
main_app()
