import streamlit as st
import os
from firebase import read

# --- Streamlit Page Configuration ---
# Use 'expanded' for a larger, default-open sidebar post-login
st.set_page_config(
    page_title="OMS System", 
    layout="wide", 
    initial_sidebar_state="expanded" 
)

# --- Custom CSS for Enhanced Sidebar UI ---
# Injecting CSS for a modern, sticky, and colorful sidebar
st.markdown("""
<style>
    /* 1. Global App Background and Font */
    .stApp {
        background-color: #f0f2f6; /* Light gray background */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* 2. Login Screen Styling (Re-applied for consistency) */
    /* Hide Sidebar and Menu until login is complete */
    .stApp:has([data-testid="stSidebar"]) { 
        background-image: url('https://images.unsplash.com/photo-1520880867055-1e30d1cb001c');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp:has([data-testid="stSidebar"]) [data-testid="stSidebar"], 
    .stApp:has([data-testid="stSidebar"]) [data-testid="stToolbar"], 
    .stApp:has([data-testid="stSidebar"]) [data-testid="stHeader"] {
        display: none !important;
    }

    /* 3. Sidebar Container Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff; /* White background for the sidebar */
        box-shadow: 2px 0 10px rgba(0,0,0,0.1); /* Subtle shadow for depth */
        transition: width 0.3s ease-in-out;
    }
    
    /* 4. Sidebar Header/Title Styling */
    .sidebar-header {
        padding: 20px 20px 10px 20px;
        color: #1E90FF; /* Primary blue for title */
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 15px;
    }
    
    /* 5. Radio Button (Navigation) Styling */
    /* Target the container of the radio buttons */
    [data-testid="stSidebar"] .stRadio > div {
        padding: 0 10px;
    }

    /* Style the labels (the actual menu items) */
    [data-testid="stSidebar"] .stRadio label {
        padding: 12px 15px;
        margin-bottom: 5px;
        border-radius: 8px;
        transition: all 0.2s;
        font-weight: 500;
    }
    
    /* Hover state */
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #f0f8ff; /* Light blue on hover */
        color: #1E90FF;
        cursor: pointer;
    }

    /* Selected/Checked state */
    [data-testid="stSidebar"] .stRadio input:checked + div > span {
        background-color: #1E90FF !important; /* Primary blue background for selected item */
        color: white !important; /* White text for contrast */
        border-radius: 8px;
        font-weight: bold;
        padding: 12px 15px;
    }

    /* Ensure the whole button area is clickable and styled */
    [data-testid="stSidebar"] .stRadio label > span:nth-child(2) {
        width: 100%; /* Make the label fill the space */
    }
    
    /* 6. Logout Button Styling */
    [data-testid="stSidebar"] .stButton button {
        width: 90%;
        margin: 15px 5%; /* Center the button */
        background-color: #FF4B4B; /* Red for logout/warning */
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
    except Exception as e:
        # print(f"Firebase read error for user {username}: {e}")
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

# --- Login Screen (Kept mostly the same for glassmorphism effect) ---

def login_screen():
    """Displays the beautiful, centered login interface."""
    # Custom CSS for login form visibility on background
    st.markdown("""
    <style>
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
        
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
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

# --- Admin Sidebar & Routing (Updated) ---

def admin_sidebar():
    """
    Displays the full, beautifully styled navigation sidebar for 'admin' users.
    """
    # Custom Header for the Sidebar
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

    # Map keys to strings with emojis for better display in the radio
    display_options = [f"{icon} {key}" for key, (icon, file) in ADMIN_MENU.items()]
    
    # Get the index of the current selection for pre-selection
    current_key = st.session_state.admin_menu_choice
    current_index = list(ADMIN_MENU.keys()).index(current_key) if current_key in ADMIN_MENU else 0
    
    st.sidebar.markdown("### **🧭 Main Navigation**")
    
    # Create the radio button menu
    choice_with_icon = st.sidebar.radio(
        "", # Empty label, as we use the markdown header
        display_options,
        index=current_index,
        key="admin_radio_menu" 
    )

    # Extract the plain key from the choice (e.g., "Create Order" from "📦 Create Order")
    # This assumes the key is everything after the first space (i.e., after the emoji)
    choice = " ".join(choice_with_icon.split(" ")[1:])

    # Update session state and rerun if the choice changes
    if choice != st.session_state.admin_menu_choice:
         st.session_state.admin_menu_choice = choice
         st.rerun() 

    # Load the selected page
    _, file = ADMIN_MENU[st.session_state.admin_menu_choice]
    load_page(file)
    
    # Add a prominent logout button
    st.sidebar.markdown("---")
    # The logout button is styled by the custom CSS in section 6
    st.sidebar.button("Logout", on_click=logout) 


# --- Departmental Routing ---

def department_router():
    """Routes a non-admin user directly to their assigned department page."""
    role = st.session_state.get("role")
    
    # Simple, clean sidebar for department users
    st.sidebar.markdown(f"### ⚙️ Your Department: **{role.title()}**")
    st.sidebar.markdown("---")
    st.sidebar.button("Logout", on_click=logout, type="primary")

    file = DEPARTMENT_PAGE_MAP.get(role)

    if file:
        load_page(file)
    else:
        st.error(f"Your role **{role}** is not assigned to a department page.")

# --- Application Entry Point ---

def main_app():
    """Main function to handle post-login routing."""
    # Main content header
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

if "role" not in st.session_state:
    login_screen()
else:
    main_app()
