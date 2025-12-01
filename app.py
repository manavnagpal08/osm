import streamlit as st
import os
from firebase import read

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="OMS System", 
    layout="wide", 
    initial_sidebar_state="collapsed" 
)

# --- Constants ---
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "admin123",
    "role": "admin"
}

# ⭐ FIX: Corrected the routing for the 'design' department 
# 🚀 ADD: Added the 'lamination' department
DEPARTMENT_PAGE_MAP = {
    "design": "design.py",
    "printing": "printing.py",
    "lamination": "lamination.py", # NEW DEPARTMENT
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
            st.error(f"Error loading page **{page_file}**: {e}")
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
    """Injects all global and local styles, optimized for the standard size and ultimate beautiful sidebar."""
    
    st.markdown("""
    <style>
        /* Global App Styling */
        .stApp {
            /* Main content area is pure white */
            background-color: #FFFFFF; 
            font-family: 'Poppins', sans-serif;
        }

        /* ------------------------------------------------------------- */
        /* LOGIN SCREEN STYLING (Hidden sidebar, custom background) */
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
        .stApp:has(.login-container) [data-testid="stSidebar"] {
            display: none !important;
        }

        /* 🚀 FIX: Hide header for authenticated users in the main app */
        .stApp:not(:has(.login-container)) [data-testid="stHeader"] {
            display: none !important;
        }

        /* Login Card Styles */
        .login-container {
            backdrop-filter: blur(12px);
            background: rgba(255,255,255,0.18);
            padding: 40px;
            border-radius: 16px;
            width: 380px;
            margin: auto; /* Removed fixed margin-top */
            margin-top: 140px; /* Re-added margin-top for vertical position */
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
        /* ADMIN SIDEBAR STYLING (Standard Size & Ultimate Aesthetics) */
        /* ------------------------------------------------------------- */
        
        /* Sidebar Container: Proper size (250px) and dark gradient */
        .stApp:not(:has(.login-container)) [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1f2833 0%, #12181d 100%);
            box-shadow: 4px 0 25px rgba(0,0,0,0.7);
            /* Standard Sidebar Size */
            width: 250px !important; 
            min-width: 250px !important; 
            transition: all 0.3s ease-in-out;
        }
        
        /* Sidebar Header/Title Styling */
        .sidebar-header {
            padding: 25px 15px 10px 15px; /* Reduced padding for size */
            color: #f6f9fc;
            font-size: 24px; /* Reduced size for 250px width */
            font-weight: 800;
            text-align: center;
            /* Gradient Underline */
            border-bottom: 2px solid;
            border-image: linear-gradient(to right, #00BFFF, #1E90FF) 1;
            margin-bottom: 25px;
            text-shadow: 0 1px 3px rgba(0,0,0,0.5);
        }

        /* Navigation Links Container */
        [data-testid="stSidebar"] .stRadio > div { padding: 0 5px; } /* Reduced horizontal padding */
        
        /* FIX: Ensure all text elements are white/light for contrast, and add text shadow */
        [data-testid="stSidebar"] .stRadio label * {
            color: #f6f9fc !important;
            text-shadow: 0 0 4px rgba(0, 0, 0, 0.4); /* Subtle text shadow */
        }

        /* Style the labels (the actual menu items) - Frosted Glass Look */
        [data-testid="stSidebar"] .stRadio label {
            padding: 12px 15px; /* Adjusted padding */
            margin-bottom: 6px; 
            border-radius: 8px; /* Slightly smaller radius for 250px width */
            
            /* Frosted Look */
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            
            transition: all 0.2s ease-in-out; 
            font-weight: 500;
            font-size: 15px; 
        }
        
        /* Hover state: Stronger glow and color change */
        [data-testid="stSidebar"] .stRadio label:hover {
            background-color: rgba(0, 191, 255, 0.2);
            color: #00BFFF !important;
            transform: translateX(2px) scale(1.01); 
            box-shadow: 0 4px 15px rgba(0, 191, 255, 0.3);
            cursor: pointer;
        }
        
        /* FIX for hover text color (must target the inner span) */
        [data-testid="stSidebar"] .stRadio label:hover * {
            color: #00BFFF !important; 
        }

        /* Selected/Checked state: Solid Electric Blue Highlight */
        [data-testid="stSidebar"] .stRadio input:checked + div > span {
            background-color: #00BFFF !important; /* Electric Blue */
            color: white !important; 
            border-radius: 8px;
            font-weight: 700;
            padding: 12px 15px;
            box-shadow: 0 4px 15px rgba(0, 191, 255, 0.5);
        }

        /* Logout Button Styling: Prominent and separated */
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
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: #00BFFF;
            transform: scale(1.02);
        }
    </style>
    """, unsafe_allow_html=True)

# --- Login Screen ---

def login_screen():
    """Displays the login interface."""
    
    # ⭐ FIX: Center columns FIRST
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # START container INSIDE col2 (important!)
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

        # Form prevents rerun glitches, clear_on_submit=False is the default but added for clarity
        with st.form("login_form", clear_on_submit=False):

            username = st.text_input("Username", key="login_username_input", autocomplete="username")
            password = st.text_input("Password", type="password", key="login_password_input", autocomplete="current-password")

            submitted = st.form_submit_button("Login")

            if submitted:
                username_clean = username.strip()
                password_clean = password.strip()

                if not username_clean or not password_clean:
                    st.error("Please enter both username and password.")
                    return # Exit the submitted block

                user = get_user(username_clean)

                if not user:
                    st.error("User not found.")
                    return

                if user.get("password") != password_clean:
                    st.error("Incorrect password.")
                    return

                st.session_state.username = username_clean
                st.session_state.role = user["role"]

                st.success("Login successful! Redirecting...")
                st.rerun() # Trigger the main_app() function

        # END container
        st.markdown("</div>", unsafe_allow_html=True) 

# --- Admin Sidebar & Routing ---

def admin_sidebar():
    """Displays the ultimate beautifully styled navigation sidebar for 'admin' users."""
    
    st.sidebar.markdown('<div class="sidebar-header">📦 OMS Admin</div>', unsafe_allow_html=True)

    ADMIN_MENU = {
        "Create Order": ("📦", "create_order.py"),
        "Design Dept": ("🎨", "design.py"),
        "Printing Dept": ("🖨️", "printing.py"),
        "Lamination Dept": ("🛡️", "lamination.py"), # NEW ENTRY
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
    
    with st.container(border=True):
        st.markdown(f"## ⚙️ Welcome to the **{role.title()}** Department Portal")
        st.markdown("Please manage your assigned orders below.")
        st.button("Logout", on_click=logout) 

    file = DEPARTMENT_PAGE_MAP.get(role)

    if file:
        load_page(file)
    else:
        st.error(f"Your role **{role}** is not assigned to a department page.")

# --- Application Entry Point ---

def main_app():
    """Main function to handle post-login routing."""
    
    # Title is now visible in the main content area, since the Streamlit header is hidden
    st.markdown('<h1 style="color:#3498db;"><span>📦</span> OMS Management System</h1>', unsafe_allow_html=True)
    st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")
    st.markdown("---")

    # Routing based on role
    if st.session_state["role"] == "admin":
        admin_sidebar()
    elif st.session_state["role"] in DEPARTMENT_PAGE_MAP:
        department_router()
    else:
        st.error(f"Your role **{st.session_state['role']}** is not authorized to view any page. Please contact administration.")
        st.button("Logout", on_click=logout) 

# --- Main Execution Flow ---

# Inject CSS styles first
inject_global_css()

if "role" not in st.session_state:
    login_screen()
else:
    main_app()
