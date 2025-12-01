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
    # Load login.py manually (not switch_page)
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
# ADMIN → SIDEBAR NAV
# ----------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(admin_pages.keys()))
    load_page(admin_pages[choice])

# ----------------------------------------
# NON-ADMIN → AUTO LOAD THEIR PAGE
# ----------------------------------------
else:
    if role in role_pages:
        load_page(role_pages[role])
    else:
        st.error("No page assigned to your role.")
