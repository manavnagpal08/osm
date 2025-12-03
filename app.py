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
    # CRITICAL: We explicitly collapse the sidebar to ensure it's removed from the layout 
    # since we are no longer using it for navigation.
    initial_sidebar_state="collapsed"
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
    """Injects styles for the login screen and hides the default Streamlit elements."""
    
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
            background-image: url('https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEh9JgbXkHFD_68MIoMrl8sOeanj-iPFaeHPB8IaMYuwcAsNAstm3ZYY9i33sPe4BKe-iwexUYISoCen0ZBS08VV_JZG1R9Wszjv3yEyAL1BBZBn4xTarqdVloKEq9BLR6PNaBp47ao4ZdopDD3oVN1A0GIkNL0ijwB7R1eLKAYGv8LKht52gryczc57bUtS/s320/greb.png');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-color: transparent;
        }
        
        .stApp:has(.login-container) [data-testid="stHeader"], 
        .stApp:has(.login-container) [data-testid="stToolbar"], 
        /* Ensure sidebar is hidden on login page */
        .stApp:has(.login-container) [data-testid="stSidebar"] {
            display: none !important;
        }

        /* Hide Streamlit Header/Toolbar for logged-in users */
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
        /* DROP DOWN MENU STYLING (Optional Aesthetic improvements) */
        /* ------------------------------------------------------------- */
        
        /* Ensure the selectbox label is prominent */
        .stSelectbox label {
            font-size: 18px;
            font-weight: 600;
            color: #1f2833; /* Dark text for contrast */
            margin-bottom: 5px;
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

# ------------------------------------------------------------
# 🗑️ Removed admin_sidebar() function
# ------------------------------------------------------------

def admin_navigation_dropdown():
    """Displays the navigation dropdown and handles page routing for admin users."""
    
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
    
    # Format options for the Selectbox
    display_options = [f"{icon} {key}" for key, (icon, file) in ADMIN_MENU.items()]
    
    if "admin_menu_choice_key" not in st.session_state:
        # Default to the first option key
        st.session_state.admin_menu_choice_key = "Create Order"

    # Find the current selection based on the stored key
    default_index = list(ADMIN_MENU.keys()).index(st.session_state.admin_menu_choice_key)
    
    # --- Navigation Bar Layout ---
    nav_col, logout_col = st.columns([0.8, 0.2])
    
    with nav_col:
        # Create the dropdown menu
        choice_with_icon = st.selectbox(
            "Select Department/Page:", 
            options=display_options,
            index=default_index,
            key="admin_select_menu",
            label_visibility="visible"
        )
        
        # Extract the original key (e.g., "Create Order") from the icon-prefixed string
        choice = " ".join(choice_with_icon.split(" ")[1:])
        
        # If the selection changes, update the state and rerun
        if choice != st.session_state.admin_menu_choice_key:
              st.session_state.admin_menu_choice_key = choice
              st.rerun() 
              
    with logout_col:
        # Logout button aligned to the right, slightly lower to match the selectbox
        st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
        st.button("Logout", on_click=logout, use_container_width=True) 
    
    st.markdown("---")

    # Load the selected page
    file = ADMIN_MENU[st.session_state.admin_menu_choice_key][1]
    load_page(file)


# --- Departmental Routing ---

def department_router():
    """Routes a non-admin user directly to their assigned department page."""
    
    role = st.session_state.get("role")
    
    # Title and Logout button at the top
    st.markdown(f"## ⚙️ Welcome to the **{role.title()}** Department Portal")
    
    col_btn, col_spacer = st.columns([0.2, 0.8])
    with col_btn:
        st.button("Logout", on_click=logout, use_container_width=True) 

    st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")
    st.markdown("---")
    
    st.markdown("Please manage your assigned orders below.")

    file = DEPARTMENT_PAGE_MAP.get(role)

    if file:
        load_page(file)
    else:
        st.error(f"Your role **{role}** is not assigned to a department page.")

# --- Application Entry Point ---

def main_app():
    """Main function to handle post-login routing."""
    
    st.markdown('<h1 style="color:#3498db;"><span>📦</span> OMS Management System</h1>', unsafe_allow_html=True)
    st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")

    # Routing based on role
    if st.session_state["role"] == "admin":
        # Admin gets the new dropdown navigation
        admin_navigation_dropdown()
    elif st.session_state["role"] in DEPARTMENT_PAGE_MAP:
        # Departmental users go directly to their page
        department_router()
    else:
        # Fallback for unrecognized roles
        st.error(f"Your role **{st.session_state['role']}** is not authorized to view any page. Please contact administration.")
        st.button("Logout", on_click=logout) 

# --- Main Execution Flow ---

# Inject CSS styles first
inject_global_css()

# ---------------------------------------------------------
# 🚨 LOGIN ROUTING
# ---------------------------------------------------------

if "role" not in st.session_state:
    login_screen()
    st.stop()

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
