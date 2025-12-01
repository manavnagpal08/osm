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
    st.switch_page("login.py")

role = st.session_state["role"]
username = st.session_state["username"]

# ----------------------------------------
# UNIVERSAL SIDEBAR REMOVAL (WORKS 100%)
# ----------------------------------------
if role != "admin":
    st.markdown("""
        <style>
            /* Hide ALL possible sidebars */
            aside, nav, section[aria-label="sidebar"],
            [data-testid="stSidebar"], [data-testid="stSidebarNav"],
            [data-testid="collapsedControl"],
            button[kind="header"],
            div[class*="sidebar"], div[id*="sidebar"] {
                display: none !important;
                visibility: hidden !important;
                width: 0 !important;
                min-width: 0 !important;
            }

            /* Full width layout */
            [data-testid="stAppViewContainer"] {
                margin-left: 0 !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ----------------------------------------
# PAGE LOADER
# ----------------------------------------
def load_page(file_path):
    """Load a page by executing its Python file."""
    full_path = os.path.join("modules", file_path)
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            code = compile(f.read(), full_path, 'exec')
            exec(code, globals())
    else:
        st.error(f"Page not found: {file_path}")

# ----------------------------------------
# TITLE
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{username}** | Role: {role}")

# ----------------------------------------
# ROLE → PAGE MAPPING
# ----------------------------------------
role_pages = {
    "design": "create_order.py",
    "printing": "printing.py",
    "diecut": "diecut.py",
    "assembly": "assembly.py",
    "dispatch": "dispatch.py",
}

admin_pages = {
    "Create Order": "create_order.py",
    "Design Dept": "design.py",
    "Printing Dept": "printing.py",
    "Die-Cut Dept": "diecut.py",
    "Assembly Dept": "assembly.py",
    "Dispatch Dept": "dispatch.py",
}

# ----------------------------------------
# ADMIN → CUSTOM SIDEBAR
# ----------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(admin_pages.keys()))
    load_page(admin_pages[choice])

# ----------------------------------------
# NON-ADMIN → AUTO-REDIRECT TO THEIR PAGE
# ----------------------------------------
else:
    if role in role_pages:
        load_page(role_pages[role])
    else:
        st.error("Your role has no assigned page. Contact admin.")
