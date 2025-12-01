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
    st.experimental_rerun()


# ----------------------------------------
# HEADER
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{username}** | Role: **{role}**")


# ----------------------------------------
# ADMIN SIDEBAR CSS (FINAL REFINEMENTS)
# ----------------------------------------
if role == "admin":
    st.markdown("""
        <style>

        /* 1. Global Sidebar Container */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important; /* Pure White background */
            padding-top: 0px !important;
            box-shadow: 2px 0px 8px rgba(0, 0, 0, 0.05); /* Lighter, cleaner shadow */
        }
        
        [data-testid="stSidebarContent"] {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        /* 2. Logo/Title Section */
        .sidebar-logo-container {
            background-color: #1a2a47; /* Darker Navy Header */
            padding: 25px 20px;
            margin-bottom: 20px;
            color: white;
            /* Less aggressive curve, looks cleaner */
            border-bottom-right-radius: 10px; 
        }
        .sidebar-logo-container h3 {
            color: #ffffff;
            margin: 0;
            font-size: 1.6rem; /* Slightly larger title */
            font-weight: 700;
        }
        .sidebar-logo-container p {
            color: #a0aec0;
            margin: 0;
            font-size: 0.85rem;
        }

        /* 3. Navigation Section Title */
        .sidebar-title {
            font-size: 0.9rem; /* Smaller, cleaner title */
            font-weight: 600;
            margin: 0 20px 15px 20px; 
            color: #52668b;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-top: 1px solid #f0f4f8;
            padding-top: 15px;
        }

        /* 4. Menu Item Button Styling */
        .stButton>button {
            width: 90%; 
            margin-left: 5%; 
            text-align: left;
            padding: 12px 18px;
            border-radius: 8px; /* Consistent rounding */
            margin-bottom: 4px; /* Less gap between items */
            font-size: 1rem;
            font-weight: 500;
            color: #334155;
            border: 2px solid transparent; /* Added border for hover/active state */
            background-color: transparent;
            display: flex;
            gap: 15px;
            align-items: center;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            background-color: #f7f9fd; /* Very light hover */
            color: #1e293b;
            border: 2px solid #cbd5e1; /* Light border on hover */
            transform: none;
        }

        /* 5. Active Menu Item (Focus on border/text color) */
        .menu-item-active button {
            background-color: #eef2ff !important; /* Very light blue background */
            color: #4f46e5 !important; /* Stronger accent color */
            font-weight: 600 !important;
            border: 2px solid #6366f1 !important; /* Primary blue border highlights the active tab */
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); 
        }
        .menu-item-active button:hover {
            background-color: #eef2ff !important; 
            color: #4f46e5 !important;
        }
        
        /* 6. Logout Button (Sticky Footer) */
        .logout-container {
            padding: 20px 15px;
            margin-top: auto; 
            border-top: 1px solid #e0e0e0;
            background-color: #ffffff;
        }

        .logout-container .stButton button {
            background-color: #dc2626; /* Strong Red */
            color: white;
            font-weight: 600;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(220, 38, 38, 0.2);
            width: 100%;
            margin: 0;
            border: none;
        }
        .logout-container .stButton button:hover {
            background-color: #b91c1c;
            transform: none;
            border: none;
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
    "Packaging": ("🎁", "packaging.py"), # RENAMED DISPATCH TO PACKAGING
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
        "packaging": "packaging.py", # Mapped 'packaging' role to the new file
    }

    if role in role_pages:
        load_page(role_pages[role])
    else:
        st.error(f"No page assigned to your role: **{role}**.")
