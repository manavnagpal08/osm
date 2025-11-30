import streamlit as st

st.set_page_config(page_title="OMS Dashboard", layout="wide")

# Block if not logged in
if "role" not in st.session_state:
    st.switch_page("login.py")

role = st.session_state["role"]

st.title("📦 Order Management System")
st.caption(f"Logged in as **{st.session_state['username']}** | Role: **{role}**")

# -------------------------------
# CUSTOM ROLE-BASED NAVIGATION
# -------------------------------
pages = {}

if role in ["admin", "design"]:
    pages["Create Order"] = "secure_pages/create_order.py"
    pages["Design Dept"] = "secure_pages/design.py"

if role in ["admin", "printing"]:
    pages["Printing Dept"] = "secure_pages/printing.py"

if role in ["admin", "diecut"]:
    pages["Die-Cut Dept"] = "secure_pages/diecut.py"

if role in ["admin", "assembly"]:
    pages["Assembly Dept"] = "secure_pages/assembly.py"

if role in ["admin", "dispatch"]:
    pages["Dispatch Dept"] = "secure_pages/dispatch.py"

choice = st.sidebar.selectbox("Navigate", list(pages.keys()))
st.switch_page(pages[choice])
