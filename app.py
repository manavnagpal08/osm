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
    with open("login.py", "r") as f:
        exec(f.read())
    st.stop()

role = st.session_state["role"]
username = st.session_state["username"]


# ----------------------------------------
# REMOVE SIDEBAR IF NOT ADMIN
# ----------------------------------------
if role != "admin":
    st.markdown("""
        <style>
            aside, nav, section[aria-label="sidebar"],
            [data-testid="stSidebar"], [data-testid="stSidebarNav"],
            [data-testid="collapsedControl"], button[kind="header"] {
                display: none !important;
                visibility: hidden !important;
            }

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
    full_path = os.path.join("modules", file)
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            exec(f.read(), globals())
    else:
        st.error(f"Page not found: {file}")


# ----------------------------------------
# HEADER
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{username}** | Role: {role}")


# ----------------------------------------
# ADMIN SIDEBAR CSS (ICONS + ACTIVE STYLE)
# ----------------------------------------
if role == "admin":
    st.markdown("""
        <style>

        /* Sidebar container */
        [data-testid="stSidebar"] {
            background-color: #f8f9fc !important;
            padding-top: 20px !important;
        }

        /* Sidebar section title */
        .sidebar-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 15px;
            color: #1f2937;
        }

        /* Menu item */
        .menu-item {
            padding: 10px 14px;
            border-radius: 10px;
            margin-bottom: 6px;
            font-size: 1rem;
            font-weight: 500;
            color: #2d3748;
            display: flex;
            gap: 10px;
            align-items: center;
            cursor: pointer;
            transition: 0.2s;
        }

        /* Hover effect */
        .menu-item:hover {
            background-color: #e2e8f0;
            color: #1a202c;
        }

        /* Active menu item */
        .menu-item-active {
            background-color: #dbeafe !important;
            color: #1e3a8a !important;
            font-weight: 700 !important;
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

    st.sidebar.markdown("<div class='sidebar-title'>🧭 Navigation</div>", unsafe_allow_html=True)

    # Track active selection
    if "active_menu" not in st.session_state:
        st.session_state.active_menu = "Create Order"

    # Draw menu items
    for label, (icon, file) in admin_menu.items():
        active = "menu-item-active" if st.session_state.active_menu == label else ""
        if st.sidebar.button(f"{icon} {label}", key=label):
            st.session_state.active_menu = label

    # Load selected page
    selected_file = admin_menu[st.session_state.active_menu][1]
    load_page(selected_file)


# ----------------------------------------
# NON-ADMIN → AUTO LOAD THEIR PAGE
# ----------------------------------------
else:
    role_pages = {
        "design": "create_order.py",
        "printing": "printing.py",
        "diecut": "diecut.py",
        "assembly": "assembly.py",
        "dispatch": "dispatch.py",
    }

    if role in role_pages:
        load_page(role_pages[role])
    else:
        st.error("No page assigned to your role.")
