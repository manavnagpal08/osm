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
# HIDE SIDEBAR FOR NON-ADMIN (CRITICAL)
# ----------------------------------------
if role != "admin":
    st.markdown("""
        <style>
            /* Hide entire sidebar */
            [data-testid="stSidebar"] {
                display: none !important;
            }

            /* Hide the navigation root (prevents ghost sidebar) */
            [data-testid="stSidebarNav"] {
                display: none !important;
            }

            /* Hide hamburger menu in top-left */
            button[kind="header"] {
                display: none !important;
            }

            /* Hide toggle sidebar button (new Streamlit versions) */
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            /* Use full width */
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
# ADMIN → SHOW SIDEBAR MENU
# ----------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(pages.keys()))
    st.switch_page(pages[choice])

# ----------------------------------------
# NON-ADMIN → AUTO-REDIRECT TO THEIR PAGE
# ----------------------------------------
else:
    # They must have exactly ONE assigned page
    if len(pages) == 1:
        only_page = list(pages.values())[0]
        st.switch_page(only_page)
    else:
        st.error("No page assigned to your role. Contact admin.")
