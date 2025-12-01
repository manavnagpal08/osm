import streamlit as st
import os
from firebase import read

# --- Streamlit Page Configuration ---
# Set to 'collapsed' by default to handle non-admin users who shouldn't see it.
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
    
    st.markdown("""
    <style>
        /* Global App Styling (Post-Login) */
        .stApp {
            /* Set the overall background of the application (excluding sidebar) to pure white */
            background-color: #FFFFFF; 
            font-family: 'Poppins', sans-serif; /* Use a modern font (if available) */
        }

        /* ------------------------------------------------------------- */
        /* LOGIN SCREEN STYLING: Hidden elements & Background Image */
        /* ------------------------------------------------------------- */
        .stApp:has(.login-container) {
            background-image: url('https://images.unsplash.com/photo-1520880867055-1e30d1cb001c');
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

        /* Login Card Styles (Kept the stylish glassmorphism) */
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
        /* ... other login styles remain ... */
        
        /* ------------------------------------------------------------- */
        /* ADMIN SIDEBAR STYLING (Premium Enhancement) */
        /* ------------------------------------------------------------- */
        
        /* Sidebar Container: Dark gradient and strong shadow */
        .stApp:not(:has(.login-container)) [data-testid="stSidebar"] {
            /* Dark Blue Gradient for a premium feel */
            background: linear-gradient(180deg, #2c3e50 0%, #1a242f 100%);
            box-shadow: 4px 0 20px rgba(0,0,0,0.4); /* Deeper shadow */
            width: 280px !important; 
            min-width: 280px !important; 
            transition: all 0.3s ease-in-out;
        }
        
        /* Sidebar Header/Title Styling */
        .sidebar-header {
            padding: 30px 20px 10px 20px;
            color: #ecf0f1;
            font-size: 26px; /* Slightly larger */
            font-weight: 700; /* Bolder */
            text-align: center;
            /* Use a gradient underline for extra pop */
            border-bottom: 2px solid;
            border-image: linear-gradient(to right, #2980b9, #1abc9c) 1;
            margin-bottom: 25px;
        }

        /* Navigation Links Container */
        [data-testid="stSidebar"] .stRadio > div { padding: 0 15px; }

        /* Style the labels (the actual menu items) */
        [data-testid="stSidebar"] .stRadio label {
            color: #bdc3c7; /* Subtle light gray text */
            padding: 12px 15px;
            margin-bottom: 8px; /* More spacing */
            border-radius: 8px; /* Rounder corners */
            transition: all 0.2s ease-in-out; /* Smooth transition */
            font-weight: 500;
            font-size: 15px;
        }
        
        /* Hover state: Subtle lift and bright color */
        [data-testid="stSidebar"] .stRadio label:hover {
            background-color: rgba(44, 62, 80, 0.4); /* Lighter dark background */
            color: #f1c40f; /* Vibrant yellow/gold for hover text */
            transform: translateX(5px); /* Slide effect */
            cursor: pointer;
        }

        /* Selected/Checked state: Solid active color */
        [data-testid="stSidebar"] .stRadio input:checked + div > span {
            /* Vibrant teal background */
            background-color: #1abc9c !important; 
            color: white !important; 
            border-radius: 8px;
            font-weight: 700;
            padding: 12px 15px;
            box-shadow: 0 4px 10px rgba(26, 188, 156, 0.3); /* Shadow for lift */
        }
        
        /* Styling the emoji icons within the labels */
        [data-testid="stSidebar"] .stRadio label > span:first-child {
            margin-right: 10px;
        }


        /* Logout Button Styling */
        [data-testid="stSidebar"] .stButton button {
            width: 90%;
            margin: 25px 5% 15px 5%; /* More margin at the top */
            background-color: #e74c3c; 
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            padding: 10px;
            transition: background-color 0.2s;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background-color: #c0392b;
            transform: scale(1.02); /* Slight scale on hover */
        }
    </style>
    """, unsafe_allow_html=True)

# --- Login Screen ---

def login_screen():
    """Displays the login interface."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True) 
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
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

    st.markdown("</div>", unsafe_allow_html=True) 

# --- Admin Sidebar & Routing ---

def admin_sidebar():
    """Displays the full, beautifully styled navigation sidebar for 'admin' users."""
    
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
    
    # Simple, non-styled navigation header (the main styling comes from the radio buttons)
    st.sidebar.markdown("### **🧭 Navigation**", unsafe_allow_html=True)
    
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
    
    # Simple, clean interface for department users (no sidebar visible)
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
    
    # Main content header
    st.markdown("<h1><span style='color:#3498db;'>📦</span> OMS Management System</h1>", unsafe_allow_html=True)
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
