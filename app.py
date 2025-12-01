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
    # load login manually
    with open("login.py", "r") as f:
        exec(f.read())
    st.stop()

role = st.session_state["role"]
username = st.session_state["username"]


# ----------------------------------------
# REMOVE SIDEBAR FOR NON-ADMIN
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
# PAGE LOADER
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
# ADMIN SIDEBAR CSS (BEAUTIFUL VERSION)
# ----------------------------------------
if role == "admin":
    st.markdown("""
        <style>

        /* Sidebar background gradient */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #eef2ff 0%, #f8faff 100%) !important;
            padding: 25px 18px !important;
        }

        /* Sidebar title */
        .sidebar-title {
            font-size: 1.4rem;
            font-weight: 800;
            color: #1e293b;
            margin-bottom: 20px;
            letter-spacing: -0.5px;
        }

        /* Menu item container */
        .menu-button {
            width: 100%;
            display: block;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 10px;
            font-size: 1.05rem;
            font-weight: 600;
            color: #334155;
            background-color: #ffffff;
            box-shadow: 0px 2px 4px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
            border: 1px solid #e2e8f0;
        }

        /* Hover */
        .menu-button:hover {
            background-color: #f1f5ff;
            border-color: #c7d2fe;
            transform: translateX(4px);
        }

        /* Active */
        .menu-button-active {
            background: #dbeafe !important;
            font-weight: 800 !important;
            border-color: #93c5fd !important;
            color: #1e3a8a !important;
            transform: translateX(6px);
            box-shadow: 0px 3px 6px rgba(0,0,0,0.06) !important;
        }

        </style>
    """, unsafe_allow_html=True)


# ----------------------------------------
# ADMIN MENU (WITH PACKAGING)
# ----------------------------------------
admin_menu = {
    "Create Order": ("📦", "create_order.py"),
    "Design Dept": ("🎨", "design.py"),
    "Printing Dept": ("🖨️", "printing.py"),
    "Die-Cut Dept": ("✂️", "diecut.py"),
    "Assembly Dept": ("🔧", "assembly.py"),
    "Packaging Dept": ("📦✨", "packaging.py"),  # UPDATED
}


# ----------------------------------------
# ADMIN SIDEBAR RENDERING
# ----------------------------------------
if role == "admin":

    st.sidebar.markdown(
        "<div class='sidebar-title'>🧭 Navigation</div>",
        unsafe_allow_html=True
    )

    # Track active menu
    if "active_menu" not in st.session_state:
        st.session_state.active_menu = "Create Order"

    # Render all menu items
    for label, (icon, file) in admin_menu.items():
        active_class = "menu-button-active" if st.session_state.active_menu == label else "menu-button"
        
        html_button = f"""
            <button class="{active_class}" onclick="window.location.href='?menu={label}'">
                {icon} &nbsp; {label}
            </button>
        """

        st.sidebar.markdown(html_button, unsafe_allow_html=True)

    # URL param click handling
    menu_param = st.query_params.get("menu", [None])[0]
    if menu_param in admin_menu:
        st.session_state.active_menu = menu_param

    # Load page
    selected_file = admin_menu[st.session_state.active_menu][1]
    load_page(selected_file)


# ----------------------------------------
# NON-ADMIN → AUTO PAGE
# ----------------------------------------
else:
    role_pages = {
        "design": "create_order.py",
        "printing": "printing.py",
        "diecut": "diecut.py",
        "assembly": "assembly.py",
        "dispatch": "packaging.py",
        "packaging": "packaging.py",
    }

    if role in role_pages:
        load_page(role_pages[role])
    else:
        st.error("Your role has no assigned page.")
