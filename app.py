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
    try:
        with open("login.py", "r") as f:
            exec(f.read())
        st.stop()
    except FileNotFoundError:
        st.error("Login file (login.py) not found. Cannot start.")
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
    st.rerun()


# ----------------------------------------
# HEADER
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{username}** | Role: **{role}**")


# ----------------------------------------
# ADMIN SIDEBAR CSS (SUPER ENHANCED STYLING)
# ----------------------------------------
if role == "admin":
    st.markdown("""
        <style>

        /* 1. Global Sidebar Container */
        [data-testid="stSidebar"] {
            background-color: #f7f9fd !important; /* Very light background */
            padding-top: 0px !important;
            box-shadow: 4px 0px 10px rgba(0, 0, 0, 0.03); /* Subtle, deep shadow */
        }
        
        /* Ensures sidebar content scrolls if needed */
        [data-testid="stSidebarContent"] {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        /* 2. Logo/Title Section */
        .sidebar-logo-container {
            background-color: #0b1a38; /* Deep Charcoal Blue Header */
            padding: 25px 20px;
            margin-bottom: 20px;
            color: white;
            border-bottom-right-radius: 20px; /* Slight curve for elegance */
        }
        .sidebar-logo-container h3 {
            color: #ffffff;
            margin: 0;
            font-size: 1.5rem;
            font-weight: 800;
        }
        .sidebar-logo-container p {
            color: #a0aec0;
            margin: 0;
            font-size: 0.9rem;
        }

        /* 3. Navigation Section Title */
        .sidebar-title {
            font-size: 1rem;
            font-weight: 600;
            margin: 0 20px 15px 20px; 
            color: #52668b;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            border-top: 1px solid #e2e8f0;
            padding-top: 15px;
        }

        /* 4. Menu Item Button Styling */
        .stButton>button {
            width: 90%; /* Smaller width for centered appearance */
            margin-left: 5%; /* Centering */
            text-align: left;
            padding: 12px 18px;
            border-radius: 12px; /* More rounded corners */
            margin-bottom: 8px;
            font-size: 1.05rem;
            font-weight: 500;
            color: #3f5175;
            border: none;
            background-color: transparent;
            display: flex;
            gap: 15px;
            align-items: center;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #e6eaf0; /* Softer hover color */
            color: #1a202c;
            transform: translateY(-1px); /* Little lift effect */
        }

        /* 5. Active Menu Item */
        .menu-item-active button {
            background-color: #2c52ed !important; /* Vibrant Primary Blue */
            color: white !important;
            font-weight: 700 !important;
            box-shadow: 0 5px 15px rgba(44, 82, 237, 0.3); /* Stronger shadow */
            transform: none !important;
        }
        .menu-item-active button:hover {
            background-color: #2544c4 !important; /* Darker on hover */
            color: white !important;
        }
        
        /* 6. Logout Button (Sticky Footer) */
        .logout-container {
            padding: 20px 15px;
            margin-top: auto; /* Pushes content above it up */
            border-top: 1px solid #e0e0e0;
            background-color: #ffffff; /* White background for contrast */
        }

        /* Styling for the Logout Button inside the container */
        .logout-container .stButton button {
            background-color: #f56565; /* Soft Red for warning/exit */
            color: white;
            font-weight: 600;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(245, 101, 101, 0.3);
            width: 100%;
            margin: 0;
            margin-bottom: 0;
            transform: none;
        }
        .logout-container .stButton button:hover {
            background-color: #e53e3e;
            transform: none;
        }


        </style>
    """, unsafe_allow_html=True)


# ----------------------------------------
# ADMIN MENU (LABEL, ICON, FILE)
# ----------------------------------------
admin_menu = {
    "New Order": ("➕", "create_order.py"),
    "Design": ("🖼️", "design.py"),
    "Printing": ("🖨️", "printing.py"),
    "Die-Cut": ("🔪", "diecut.py"),
    "Assembly": ("🛠️", "assembly.py"),
    "Dispatch": ("🚀", "dispatch.py"),
}


# ----------------------------------------
# ADMIN → CLICKABLE SIDEBAR MENU
# ----------------------------------------
if role == "admin":

    # --- 1. LOGO/TITLE SECTION ---
    st.sidebar.markdown(
        """
        <div class='sidebar-logo-container'>
            <h3>📦 OMS Pro</h3>
            <p>Admin Operations</p>
        </div>
        """, unsafe_allow_html=True
    )
    
    # --- 2. NAVIGATION SECTION ---
    st.sidebar.markdown("<div class='sidebar-title'>Navigation</div>", unsafe_allow_html=True)

    # Track active selection
    if "active_menu" not in st.session_state:
        st.session_state.active_menu = "New Order"

    # Draw menu items
    for label, (icon, file) in admin_menu.items():
        is_active = st.session_state.active_menu == label
        active_class = "menu-item-active" if is_active else ""
        
        st.sidebar.markdown(f"<div class='{active_class}'>", unsafe_allow_html=True)
        if st.sidebar.button(f"{icon} {label}", key=label, use_container_width=True):
            st.session_state.active_menu = label
        st.sidebar.markdown("</div>", unsafe_allow_html=True)


    # --- 3. LOGOUT SECTION (Sticky Footer) ---
    st.sidebar.markdown("<div class='logout-container'>", unsafe_allow_html=True)
    st.sidebar.button("🚪 Logout", on_click=logout, key="logout_btn", use_container_width=True)
    st.sidebar.markdown("</div>", unsafe_allow_html=True)
    
    # Load selected page
    selected_file = admin_menu[st.session_state.active_menu][1]
    load_page(selected_file)


# ----------------------------------------
# NON-ADMIN → AUTO LOAD THEIR PAGE
# ----------------------------------------
else:
    role_pages = {
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
