import streamlit as st
import os

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="OMS Dashboard", layout="wide")

# ----------------------------------------
# LOGIN CHECK
# ----------------------------------------
if "role" not in st.session_state:
    # --- NOTE: This assumes a file named 'login.py' exists in the same directory ---
    # The 'login.py' file must set st.session_state['role'] and st.session_state['username']
    try:
        with open("login.py", "r") as f:
            # We use exec to run the login logic in the current scope
            exec(f.read())
        st.stop()
    except FileNotFoundError:
        st.error("Login file (login.py) not found. Please create it.")
        st.stop()

role = st.session_state["role"]
username = st.session_state["username"]


# ----------------------------------------
# REMOVE SIDEBAR IF NOT ADMIN (Non-Admin View)
# ----------------------------------------
if role != "admin":
    st.markdown("""
        <style>
            /* Hides the default Streamlit sidebar components for non-admin roles */
            aside, nav, section[aria-label="sidebar"],
            [data-testid="stSidebar"], [data-testid="stSidebarNav"],
            [data-testid="collapsedControl"], button[kind="header"] {
                display: none !important;
                visibility: hidden !important;
            }

            /* Ensures content fills the full width when sidebar is hidden */
            [data-testid="stAppViewContainer"] {
                margin-left: 0 !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)


# ----------------------------------------
# PAGE LOADER FUNCTION
# ----------------------------------------
def load_page(file):
    """Loads and executes the code from a Python file within the 'modules' directory."""
    full_path = os.path.join("modules", file)
    if os.path.exists(full_path):
        try:
            with open(full_path, "r") as f:
                # Use globals() to ensure module code runs in the main app's scope
                exec(f.read(), globals())
        except Exception as e:
             st.error(f"Error loading page '{file}': {e}")
    else:
        st.error(f"Page not found: 'modules/{file}'.")


# ----------------------------------------
# LOGOUT FUNCTION
# ----------------------------------------
def logout():
    """Clears the session state and triggers a rerun to go back to the login screen."""
    st.session_state.clear()
    st.experimental_rerun()


# ----------------------------------------
# HEADER
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{username}** | Role: **{role}**")


# ----------------------------------------
# ADMIN SIDEBAR CSS (ENHANCED STYLING)
# ----------------------------------------
if role == "admin":
    st.markdown("""
        <style>

        /* Sidebar container - Added shadow and white background */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important; /* White background */
            padding-top: 0px !important;
            box-shadow: 2px 0px 5px rgba(0, 0, 0, 0.05); /* Subtle shadow */
        }

        /* Streamlit's native sidebar navigation container */
        [data-testid="stSidebarNav"] {
            padding-top: 0 !important;
        }

        /* Custom section for Title/Logo space */
        .sidebar-logo-container {
            padding: 20px 15px;
            border-bottom: 1px solid #e0e0e0; /* Separator line */
            margin-bottom: 10px;
        }

        /* Sidebar section title */
        .sidebar-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin: 15px 0 10px 15px; /* Adjusted margin for better spacing */
            color: #1f2937;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Menu item button style (Streamlit button is used here) */
        .stButton>button {
            width: 100%;
            text-align: left;
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 1rem;
            font-weight: 500;
            color: #4a5568;
            border: none;
            background-color: transparent;
            display: flex;
            gap: 10px;
            align-items: center;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }

        /* Hover effect */
        .stButton>button:hover {
            background-color: #f0f4f8; /* Light gray hover */
            color: #1a202c;
        }

        /* Active menu item - Uses Streamlit's primary color or a strong accent */
        .menu-item-active button {
            background-color: #1e3a8a !important; /* A deep blue/primary color */
            color: white !important;
            font-weight: 700 !important;
            box-shadow: 0 4px 6px rgba(30, 58, 138, 0.2); /* Subtle shadow for active item */
        }
        .menu-item-active button:hover {
            background-color: #1c337a !important; /* Darker on hover */
            color: white !important;
        }
        
        /* CSS for the logout button container */
        .logout-container {
            padding: 20px 15px;
            margin-top: auto; /* Push to the bottom */
            border-top: 1px solid #e0e0e0;
        }

        </style>
    """, unsafe_allow_html=True)


# ----------------------------------------
# ADMIN MENU (LABEL, ICON, FILE)
# ----------------------------------------
admin_menu = {
    "Create Order": ("📦", "create_order.py"),
    "Design Dept": ("🎨", "design.py"),
    "Printing Dept": ("🖨️", "printing.py"),
    "Die-Cut Dept": ("✂️", "diecut.py"),
    "Assembly Dept": ("🔧", "assembly.py"),
    "Dispatch Dept": ("🚚", "dispatch.py"),
}


# ----------------------------------------
# ADMIN → CLICKABLE SIDEBAR MENU
# ----------------------------------------
if role == "admin":

    # --- 1. LOGO/TITLE SECTION ---
    st.sidebar.markdown(
        """
        <div class='sidebar-logo-container'>
            <h3 style='color: #1e3a8a; margin: 0;'>📦 OMS Admin</h3>
            <p style='font-size: 0.85rem; color: #6b7280; margin: 0;'>Navigation Dashboard</p>
        </div>
        """, unsafe_allow_html=True
    )
    
    # --- 2. NAVIGATION SECTION ---
    st.sidebar.markdown("<div class='sidebar-title'>🧭 Navigation</div>", unsafe_allow_html=True)

    # Track active selection
    if "active_menu" not in st.session_state:
        st.session_state.active_menu = "Create Order"

    # Draw menu items
    for label, (icon, file) in admin_menu.items():
        # Use a container to apply the active CSS class
        is_active = st.session_state.active_menu == label
        active_class = "menu-item-active" if is_active else ""
        
        # Place the button inside a styled container
        st.sidebar.markdown(f"<div class='{active_class}'>", unsafe_allow_html=True)
        if st.sidebar.button(f"{icon} {label}", key=label, use_container_width=True):
            st.session_state.active_menu = label
        st.sidebar.markdown("</div>", unsafe_allow_html=True)


    # --- 3. LOGOUT SECTION ---
    # Spacer to push the logout button to the bottom
    st.sidebar.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='logout-container'>", unsafe_allow_html=True)
    st.sidebar.button("🚪 Logout", on_click=logout, use_container_width=True, help="Click to log out of the system")
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    
    # Load selected page
    selected_file = admin_menu[st.session_state.active_menu][1]
    load_page(selected_file)


# ----------------------------------------
# NON-ADMIN → AUTO LOAD THEIR PAGE
# ----------------------------------------
else:
    role_pages = {
        # NOTE: A non-admin design role should probably map to 'design.py', not 'create_order.py'
        # I've updated the mapping based on department roles.
        "design": "design.py", 
        "printing": "printing.py",
        "diecut": "diecut.py",
        "assembly": "assembly.py",
        "dispatch": "dispatch.py",
    }

    if role in role_pages:
        load_page(role_pages[role])
    else:
        st.error(f"No page assigned to your role: **{role}**.")
