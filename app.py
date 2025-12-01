import streamlit as st

st.set_page_config(page_title="OMS Dashboard", layout="wide")

# --- LOGIN CHECK ---
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

role = st.session_state["role"]

st.title("📦 Order Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: {role}")

# -------------------------------
# ROLE → PAGE MAPPING
# -------------------------------
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


# ---------------------------------------------------
# SHOW SIDEBAR ONLY FOR ADMIN
# ---------------------------------------------------
if role == "admin":
    choice = st.sidebar.selectbox("Navigate", list(pages.keys()))
    st.switch_page(pages[choice])
else:
    # -----------------------------------------
    # HIDE SIDEBAR for non-admin users
    # -----------------------------------------
    hide_sidebar_style = """
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="stAppViewContainer"] {margin-left: 0;}
        </style>
    """
    st.markdown(hide_sidebar_style, unsafe_allow_html=True)

    # Auto-redirect non-admin users to THEIR only page
    if len(pages) == 1:
        only_page = list(pages.values())[0]
        st.switch_page(only_page)
    else:
        st.error("No page assigned to your role. Contact admin.")
