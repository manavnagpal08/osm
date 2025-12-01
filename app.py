import streamlit as st
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
    st.switch_page("pages/login.py")

role = st.session_state["role"]

# ----------------------------------------
# CHECK STREAMLIT VERSION FOR SIDEBAR SUPPORT
# ----------------------------------------
current_ver = version.parse(st.__version__)
can_hide_sidebar = current_ver >= version.parse("1.25.0")  # Sidebar CSS works from v1.25+

# ----------------------------------------
# HIDE SIDEBAR FOR NON-ADMIN (WITH FALLBACK)
# ----------------------------------------
if role != "admin":

    if can_hide_sidebar:
        # Try to hide using CSS
        st.markdown("""
            <style>

            /* Old Sidebar */
            [data-testid="stSidebar"] {display: none !important;}
            [data-testid="stSidebarNav"] {display: none !important;}

            /* New Sidebar (v1.36+) */
            section[data-testid="stSidebar"] {display: none !important;}
            div[data-testid="stSidebar"] {display: none !important;}

            /* Emotion-cache wrappers */
            div[class*="st-emotion-cache"][class*="sidebar"] {display: none !important;}
            aside[class*="sidebar"] {display: none !important;}

            /* Collapsed control */
            [data-testid="collapsedControl"] {display: none !important;}

            /* Hamburger */
            button[kind="header"] {display: none !important;}

            /* Full width */
            [data-testid="stAppViewContainer"] {
                margin-left: 0 !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            </style>
        """, unsafe_allow_html=True)

    else:
        # ----------------------------------------
        # FALLBACK MODE (STREAMLIT TOO OLD)
        # Force full-screen view so sidebar disappears automatically
        # ----------------------------------------
        st.markdown("""
            <style>
                /* Make main container full width */
                [data-testid="stAppViewContainer"] {
                    margin-left: 0 !important;
                    width: 100% !important;
                }

                /* Hide hamburger & collapsed icons */
                button[kind="header"] {display: none !important;}
                [data-testid="collapsedControl"] {display: none !important;}
            </style>
        """, unsafe_allow_html=True)

# ----------------------------------------
# TITLE & USER INFO
# ----------------------------------------
st.title("📦 Order Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {role} | Streamlit {st.__version__} detected")

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
# ADMIN: SHOW SIDEBAR
# ----------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(pages.keys()))
    st.switch_page(pages[choice])

# ----------------------------------------
# NON-ADMIN → AUTO-REDIRECT
# ----------------------------------------
else:
    if len(pages) == 1:
        st.switch_page(list(pages.values())[0])
    else:
        st.error("No page assigned to your role. Contact admin.")
