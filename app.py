import streamlit as st
import os
# Assuming 'firebase' is a custom module with a 'read' function
from firebase import read

# --- Streamlit Page Configuration ---
# Set to 'collapsed' by default to handle non-admin users who shouldn't see it.
# We will explicitly expand it for the admin later using CSS.
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

# Mapping of department roles to their corresponding module files
DEPARTMENT_PAGE_MAP = {
    "design": "create_order.py",
    "printing": "printing.py",
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
    """Injects common styles for the app and the login-specific styles."""
    
    # We use CSS `:has()` selector to detect if the login-container is present, 
    # ensuring the background image and sidebar hiding only occur on the login screen.
    st.markdown("""
    <style>
        /* Global App Styling (Post-Login) */
        .stApp {
            background-color: #f0f2f6; /* Light gray background for main app */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        /* ------------------------------------------------------------- */
        /* LOGIN SCREEN STYLING: ONLY when .login-container is present */
        /* ------------------------------------------------------------- */
        .stApp:has(.login-container) {
            /* 2. Show background image ONLY during login */
            background-image: url('https://images.unsplash.com/photo-1520880867055-1e30d1cb001c');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-color: transparent; /* Override main app background */
        }
        
        .stApp:has(.login-container) [data-testid="stHeader"], 
        .stApp:has(.login-container) [data-testid="stToolbar"], 
        .stApp:has(.login-container) [data-testid="stSidebar"] {
            /* 1. Hide Sidebar, Header, and Menu only during login */
            display: none !important;
        }

        /* Login Card (Glassmorphism effect) */
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
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            margin-bottom: 25px;
        }
        .stTextInput > label, .stTextInput > div > div > input {
            color: white !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }
        .stTextInput > div > div > input {
            background-color: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 8px;
            padding: 10px;
        }
        .stButton button {
            width: 100%;
            background-color: #4CAF50;
            color: white;
            border-radius: 8px;
            padding: 10px;
            font-weight: bold;
            margin-top: 10px;
        }
        
        /* ------------------------------------------------------------- */
        /* ADMIN SIDEBAR STYLING (Post-Login) */
        /* ------------------------------------------------------------- */
        
        /* 3. SHOW/EXPAND Sidebar ONLY for Admin */
        .stApp:not(:has(.login-container)) [data-testid="stSidebar"] {
            /* This ensures the sidebar is visible and expanded for non-login pages */
            width: 300px !important; /* Set desired width */
            min-width: 300px !important; 
        }

        /* 4. Hide Sidebar Collapse button for Department users (or if you want to enforce full-time expansion for Admin) */
        /* [data-testid="collapsedControl"] { display: none !important; } */
        
        [data-testid="stSidebar"] {
            background-color: #ffffff; 
            box-shadow: 2px 0 10px rgba(0,0,0,0.1); 
            transition: width 0.3s ease-in-out;
        }
        .sidebar-header {
            padding: 20px 20px 10px 20px;
            color: #1E90FF;
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 15px;
        }
        [data-testid="stSidebar"] .stRadio > div { padding: 0 10px; }
        [data-testid="stSidebar"] .stRadio label {
            padding: 12px 15px;
            margin-bottom: 5px;
            border-radius: 8px;
            transition: all 0.2s;
            font-weight: 500;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background-color: #f0f8ff;
            color: #1E90FF;
            cursor: pointer;
        }
        [data-testid="stSidebar"] .stRadio input:checked + div > span {
            background-color: #1E90FF !important;
            color: white !important;
            border-radius: 8px;
            font-weight: bold;
            padding: 12px 15px;
        }
        [data-testid="stSidebar"] .stButton button {
            width: 90%;
            margin: 15px 5%;
            background-color: #FF4B4B;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: #CC0000;
        }
    </style>
    """, unsafe_allow_html=True)

# --- Login Screen ---

def login_screen():
    """Displays the login interface and uses the .login-container class to trigger CSS."""
    # This class is crucial for the CSS to know when to hide the sidebar and apply the background image
    st.markdown('<div class="login-container">', unsafe_allow_html=True) 
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Note: The opening div tag is now *outside* this function and defined in the main flow
        # to ensure the CSS selector works against the whole app.
        st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

        with st.form("login_form"):
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

                if not user:
                    st.error("User not found.")
                    return

                if user.get("password") != password_clean:
                    st.error("Incorrect password.")
                    return

                st.session_state.username = username_clean
                st.session_state.role = user["role"]

                st.success("Login successful! Redirecting...")
                st.balloons()
                st.rerun()

    # The closing div tag is placed here
    st.markdown("</div>", unsafe_allow_html=True) 

# --- Admin Sidebar & Routing ---

def admin_sidebar():
    """Displays the full, beautifully styled navigation sidebar for 'admin' users."""
    
    # 3. SHOW SIDEBAR: The global CSS handles the expansion. We just draw the content.
    
    st.sidebar.markdown('<div class="sidebar-header">📦 OMS Admin</div>', unsafe_allow_html=True)

    ADMIN_MENU = {
        "Create Order": ("📦", "create_order.py"),
        "Design Dept": ("🎨", "design.py"),
        "Printing Dept": ("🖨️", "printing.py"),
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
    
    st.sidebar.markdown("### **🧭 Main Navigation**")
    
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
    
    # 4. HIDE SIDEBAR: The default state set in st.set_page_config is 'collapsed'.
    # For department users, we simply don't draw any content *into* the sidebar, 
    # ensuring it remains visually empty and minimized.
    
    role = st.session_state.get("role")
    
    # Use the main area to show departmental context and a logout button
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
    
    st.markdown("<h1><span style='color:#1E90FF;'>📦</span> OMS Management System</h1>", unsafe_allow_html=True)
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
    # User is not logged in, show the login screen.
    login_screen()
else:
    # User is logged in, show the main application.
    main_app()
