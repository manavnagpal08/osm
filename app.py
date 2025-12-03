import streamlit as st
import os
from firebase import read, update
import streamlit.components.v1 as components

st.set_page_config(
    page_title="OMS System",
    layout="wide"
)

# ------------------ FIX: CUSTOM SIDEBAR CSS ------------------

def inject_css():
    st.markdown("""
    <style>

    body { overflow-x: hidden; }

    /* ------------------ CUSTOM SIDEBAR ------------------ */
    #custom-sidebar {
        position: fixed;
        top: 0;
        left: 0;
        width: 250px;
        height: 100vh;
        background: #1f2833;
        padding-top: 80px;
        color: white;
        z-index: 9999;
        transition: 0.3s;
    }

    #custom-sidebar a {
        display: block;
        padding: 14px 20px;
        color: white;
        text-decoration: none;
        font-size: 16px;
    }

    #custom-sidebar a:hover {
        background: #00bcd4;
    }

    /* hide sidebar on mobile */
    @media(max-width: 768px) {
        #custom-sidebar {
            transform: translateX(-260px);
        }

        body.sidebar-open #custom-sidebar {
            transform: translateX(0);
        }

        body.sidebar-open .main-content {
            margin-left: 250px !important;
        }
    }

    /* desktop main content */
    .main-content {
        margin-left: 260px;
        padding: 20px;
    }

    /* mobile main content */
    @media(max-width: 768px) {
        .main-content {
            margin-left: 0 !important;
        }
    }

    /* hamburger */
    #hamburger-btn {
        position: fixed;
        top: 15px;
        left: 15px;
        font-size: 30px;
        background: #1f2833;
        color: white;
        padding: 8px 14px;
        border-radius: 6px;
        cursor: pointer;
        z-index: 20000;
    }

    </style>
    """, unsafe_allow_html=True)


inject_css()

# ------------------ WORKING HAMBURGER ------------------

components.html("""
    <div id="hamburger-btn">☰</div>

    <script>
        const btn = document.getElementById("hamburger-btn");
        btn.addEventListener("click", function() {
            document.body.classList.toggle("sidebar-open");
        });
    </script>
""", height=60)

# ------------------ CUSTOM SIDEBAR ------------------

def sidebar_html():
    st.markdown("""
    <div id="custom-sidebar">
        <a href="?page=create_order">📦 Create Order</a>
        <a href="?page=design">🎨 Design Dept</a>
        <a href="?page=printing">🖨 Printing Dept</a>
        <a href="?page=lamination">🛡 Lamination Dept</a>
        <a href="?page=diecut">✂️ Diecut Dept</a>
        <a href="?page=assembly">🔧 Assembly Dept</a>
        <a href="?page=packaging">📦 Packaging Dept</a>
        <a href="?page=all_orders">📋 All Orders</a>
        <a href="?page=manage_users">👤 User Management</a>
        <a href="?page=logout">🚪 Logout</a>
    </div>
    """, unsafe_allow_html=True)


sidebar_html()

# ------------------ PAGE LOADER ------------------

def load_page(page):
    filename = page + ".py"
    full_path = os.path.join("modules", filename)
    if os.path.exists(full_path):
        exec(open(full_path, "r").read(), globals())
    else:
        st.error(f"Page not found: {filename}")


# ------------------ MAIN CONTENT ------------------

params = st.experimental_get_query_params()
page = params.get("page", ["home"])[0]

st.markdown('<div class="main-content">', unsafe_allow_html=True)

if page == "logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Logged out!")
elif page == "home":
    st.title("OMS System")
    st.write("Welcome! Select a page from the menu.")
else:
    load_page(page)

st.markdown("</div>", unsafe_allow_html=True)
