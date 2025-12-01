import streamlit as st
from packaging import version

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="OMS Dashboard", layout="wide")

# ----------------------------------------
# LOGIN CHECK
# ----------------------------------------
if "role" not in st.session_state:
    st.switch_page("app_pages/login.py")

role = st.session_state["role"]

# ----------------------------------------
# UNIVERSAL SIDEBAR DISABLER (WORKS ALWAYS)
# ----------------------------------------
if role != "admin":
    st.markdown("""
        <style>

        /* REMOVE ASIDE COMPLETELY (NEW STREAMLIT) */
        aside, nav, section[aria-label="sidebar"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            min-width: 0 !important;
        }

        /* TARGET ANY POSSIBLE SIDEBAR WRAPPER */
        [id*="__sidebar__"],
        [class*="sidebar"],
        [data-testid*="sidebar"],
        [data-testid*="stSidebar"],
        div[id*="stSidebar"],
        div[class*="stSidebar"],
        div:has(nav[aria-label="Sidebar"]) {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
        }

        /* REMOVE THE HAMBURGER MENU ALWAYS */
        button[kind="header"],
        [data-testid="collapsedControl"],
        [title="Toggle sidebar"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* FORCE FULL WIDTH ALWAYS */
        .block-container, [data-testid="stAppViewContainer"] {
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            margin-left: 0 !important;
        }

        </style>
    """, unsafe_allow_html=True)

# TITLE & ROLE
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {role}")

# ----------------------------------------
# PAGE MAPPING
# ----------------------------------------
pages = {}

if role in ["admin", "design"]:
    pages["Create Order"] = "app_pages/create_order.py"
    pages["Design Dept"] = "app_pages/design.py"

if role in ["admin", "printing"]:
    pages["Printing Dept"] = "app_pages/printing.py"

if role in ["admin", "diecut"]:
    pages["Die-Cut Dept"] = "app_pages/diecut.py"

if role in ["admin", "assembly"]:
    pages["Assembly Dept"] = "app_pages/assembly.py"

if role in ["admin", "dispatch"]:
    pages["Dispatch Dept"] = "app_pages/dispatch.py"

# ----------------------------------------
# ADMIN – SHOW SIDEBAR
# ----------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(pages.keys()))
    st.switch_page(pages[choice])

# ----------------------------------------
# NON ADMIN – AUTO REDIRECT
# ----------------------------------------
else:
    if len(pages) == 1:
        st.switch_page(list(pages.values())[0])
    else:
        st.error("No page assigned to your role.")
