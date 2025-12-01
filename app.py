import streamlit as st
import os
# Assuming 'firebase' is a custom module with a 'read' function
# If you are using a standard library like firebase_admin, the import would be different.
from firebase import read

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="OMS System", 
    layout="wide", 
    initial_sidebar_state="auto" # Changed to auto for post-login
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
    """
    Retrieves user data from Firebase or returns the default admin.
    """
    try:
        # Assuming 'read' returns None or raises an error if user not found
        fb_user = read(f"users/{username}") 
        if isinstance(fb_user, dict) and "password" in fb_user and "role" in fb_user:
            return fb_user
    except Exception as e:
        # Log the error if necessary
        # print(f"Firebase read error for user {username}: {e}")
        pass # Continue to check for default admin if Firebase fails

    if username == DEFAULT_ADMIN["username"]:
        return DEFAULT_ADMIN
    
    return None

def load_page(page_file):
    """
    Dynamically loads and executes a page module from the 'modules' directory.
    """
    # Defensive check to prevent directory traversal
    if ".." in page_file or not page_file.endswith(".py"):
        st.error("Invalid page file request.")
        return

    full_path = os.path.join("modules", page_file)
    
    if os.path.exists(full_path):
        try:
            with open(full_path, "r") as f:
                # Compile the code before executing
                code = compile(f.read(), full_path, "exec")
                # Execute the code, making the module's functions/variables available globally
                exec(code, globals())
        except Exception as e:
            st.error(f"Error loading page **{page_file}**: {e}")
    else:
        st.error(f"Page module not found: **{page_file}** (Expected in the 'modules/' folder)")


def logout():
    """
    Clears session state and reruns to show the login screen.
    """
    for key in list(st.session_state.keys()):
        if key not in ["theme"]: # Preserve theme setting if applicable
            del st.session_state[key]
    st.rerun()

# --- Login Screen ---

def login_screen():
    """
    Displays the beautiful, centered login interface.
    """
    # Inject custom CSS for the stylish login
    st.markdown("""
    <style>
        /* Hide Sidebar and Menu until login is complete */
        [data-testid="stSidebar"], [data-testid="stToolbar"], [data-testid="stHeader"] {
            display: none !important;
        }

        /* Set a consistent full-screen background */
        .stApp {
            background-image: url('https://images.unsplash.com/photo-1520880867055-1e30d1cb001c');
            background-size: cover;
            background-position: center;
            background-attachment: fixed; /* Ensures the background stays put on scroll */
        }

        /* Centered Login Card with Blur effect */
        .login-container {
            backdrop-filter: blur(12px);
            background: rgba(255,255,255,0.18);
            padding: 40px;
            border-radius: 16px;
            width: 380px;
            margin: auto;
            margin-top: 140px;
            box-shadow: 0 4px 40px rgba(0,0,0,0.4); /* Stronger shadow */
            border: 1px solid rgba(255,255,255,0.3);
            text-align: left; /* Ensure form elements are aligned */
        }

        .login-title {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            color: white;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5); /* Text shadow for contrast */
            margin-bottom: 25px;
        }

        /* Style Streamlit input labels and text for visibility on background */
        .stTextInput > label, .stTextInput > div > div > input {
            color: white !important;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }
        
        .stTextInput > div > div > input {
            background-color: rgba(255, 255, 255, 0.2); /* Semi-transparent input fields */
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 8px;
            padding: 10px;
        }

        /* Style the Login button */
        .stButton button {
            width: 100%;
            background-color: #4CAF50; /* Green color for action */
            color: white;
            border-radius: 8px;
            padding: 10px;
            font-weight: bold;
            margin-top: 10px;
        }
        
    </style>
    """, unsafe_allow_html=True)

    # Center the login form on the page using columns (a Streamlit trick)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Use the custom HTML container
        st.markdown('<div class="login-container">', unsafe_allow_html=True)

        st.markdown('<div class="login-title">🔐 OMS Login</div>', unsafe_allow_html=True)

        # Use st.form for reliable button interaction
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username_input", autocomplete="username")
            password = st.text_input("Password", type="password", key="login_password_input", autocomplete="current-password")
            
            # The button inside the form will trigger a form submit and refresh
            submitted = st.form_submit_button("Login")

            if submitted:
                username_clean = username.strip()
                password_clean = password.strip()

                if not username_clean or not password_clean:
                    st.error("Please enter both username and password.")
                    # Do NOT wrap this in the div closing tag, as the Streamlit error already appears
                    # st.markdown("</div>", unsafe_allow_html=True) # REMOVED: This was causing issues
                    return

                user = get_user(username_clean)

                if not user:
                    st.error("User not found.")
                    return

                if user.get("password") != password_clean:
                    st.error("Incorrect password.")
                    return

                # Success: Set session state and rerun
                st.session_state.username = username_clean
                st.session_state.role = user["role"]

                st.success("Login successful! Redirecting...")
                st.balloons() # Little celebration!
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True) # Close the custom HTML container

# --- Admin Sidebar & Routing ---

def admin_sidebar():
    """
    Displays the full navigation sidebar for 'admin' users.
    """
    st.sidebar.markdown("### 🧭 Admin Navigation")

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

    # Initialize session state for menu choice if not present
    if "admin_menu_choice" not in st.session_state:
        st.session_state.admin_menu_choice = "Create Order"

    # Create the radio button menu
    choice = st.sidebar.radio(
        "Select Page",
        list(ADMIN_MENU.keys()),
        index=list(ADMIN_MENU.keys()).index(st.session_state.admin_menu_choice),
        key="admin_radio_menu" # Use a key for reliable state tracking
    )

    # Update session state only if the choice changes
    if choice != st.session_state.admin_menu_choice:
         st.session_state.admin_menu_choice = choice
         st.rerun() # Rerun to load the new page immediately

    # Load the selected page
    _, file = ADMIN_MENU[st.session_state.admin_menu_choice]
    load_page(file)
    
    # Add a prominent logout button
    st.sidebar.markdown("---")
    st.sidebar.button("Logout", on_click=logout, type="primary")


# --- Departmental Routing ---

def department_router():
    """
    Routes a non-admin user directly to their assigned department page.
    """
    role = st.session_state.get("role")
    
    st.sidebar.markdown(f"### ⚙️ Your Department: {role.title()}")
    st.sidebar.button("Logout", on_click=logout, type="primary")

    file = DEPARTMENT_PAGE_MAP.get(role)

    if file:
        load_page(file)
    else:
        st.error(f"Your role **{role}** is not assigned to a department page.")

# --- Application Entry Point ---

def main_app():
    """
    Main function to handle post-login routing.
    """
    # Header for the main application
    st.title("📦 OMS Management System")
    st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{st.session_state['role']}**")

    # Routing based on role
    if st.session_state["role"] == "admin":
        admin_sidebar()
    elif st.session_state["role"] in DEPARTMENT_PAGE_MAP:
        department_router()
    else:
        # Handle valid but unassigned roles (e.g., if a new role is added but no page exists)
        st.error(f"Your role **{st.session_state['role']}** is not authorized to view any page. Please contact administration.")
        st.button("Logout", on_click=logout) # Offer an escape route

# --- Main Execution Flow ---

if "role" not in st.session_state:
    # No role in session state means the user is not logged in
    login_screen()
else:
    # User is logged in, show the main application
    main_app()

# Note: st.stop() is removed from the login_screen logic. 
# st.rerun() on successful login is sufficient to move to the 'else' block
# in the main execution flow.
