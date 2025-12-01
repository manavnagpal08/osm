import streamlit as st

# ----------------------------------------
# PAGE CONFIG
# ----------------------------------------
st.set_page_config(page_title="OMS Dashboard", layout="wide")

# ----------------------------------------
# LOGIN CHECK
# ----------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

role = st.session_state["role"]

# ----------------------------------------
# HIDE SIDEBAR FOR NON-ADMIN (100% GUARANTEED)
# ----------------------------------------
if role != "admin":
    st.markdown("""
        <style>

        /* --- 1. OLD SIDEBAR --- */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* --- 2. NEW STREAMLIT SIDEBAR (1.36+) --- */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        div[data-testid="stSidebar"] {
            display: none !important;
        }

        /* --- 3. EMOTION-CACHE SIDEBAR WRAPPERS --- */
        div[class*="st-emotion-cache"][class*="sidebar"] {
            display: none !important;
        }
        aside[class*="sidebar"] {
            display: none !important;
        }

        /* --- 4. COLLAPSED SIDEBAR BUTTON --- */
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* --- 5. HAMBURGER MENU (top-left) --- */
        button[kind="header"] {
            display: none !important;
        }

        /* --- 6. PREVENT MOMENTARY SIDEBAR FLASH --- */
        div[aria-expanded="true"] {
            display: none !important;
        }
        div[data-testid="stSidebarUserContent"] {
            display: none !important;
        }

        /* --- 7. EXPAND MAIN CONTENT FULL WIDTH --- */
        [data-testid="stAppViewContainer"] {
            margin-left: 0 !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        </style>
    """, unsafe_allow_html=True)

# ----------------------------------------
# TITLE & USER INFO
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {role}")

# ----------------------------------------
# ROLE → PAGE MAPPING
# ----------------------------------------
pages = {}

if role in ["admin", "design"]:
    pages["Create Order"] = "pages/create_order.py"
    pages["Design Dept"] = "pages/design.py"

if role in ["admin", "printing"]:
    pages["Printing Dept"] = "pages/printing.py"

if role in ["admin", "diecut"]:
    pages["Die-Cut Dept"] = "pages/diecut.py"

if role in ["admin", "assembly"]:
    pages["Assembly Dept"] = "pages/assembly.py"

if role in ["admin", "dispatch"]:
    pages["Dispatch Dept"] = "pages/dispatch.py"

# ----------------------------------------
# ADMIN → SHOW SIDEBAR
# ----------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(pages.keys()))
    st.switch_page(pages[choice])

# ----------------------------------------
# NON-ADMIN → AUTO REDIRECT TO THEIR PAGE
# ----------------------------------------
else:
    if len(pages) == 1:
        only_page = list(pages.values())[0]
        st.switch_page(only_page)
    else:
        st.error("No page assigned to your role. Contact admin.")
