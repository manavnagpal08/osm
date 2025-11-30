import streamlit as st
from firebase import read, update
import base64
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="All Orders", page_icon="📑", layout="wide")

# --------------- PERMISSION CHECK --------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "design", "printing", "lamination", "diecut", "assembly", "packing", "dispatch"]:
    st.error("❌ You do not have permission to view this page.")
    st.stop()

st.title("📑 All Orders Overview")
st.caption("Search, filter, and view every order across all departments.")

# ---------------- LOAD DATA ----------------
orders = read("orders") or {}

# ------------- FILTER PANEL ----------------
st.sidebar.header("🔍 Filters")

search = st.sidebar.text_input("Search (ID / Customer / Item)")

stage_filter = st.sidebar.selectbox(
    "Stage",
    ["All", "Design", "Printing", "Lamination", "DieCut", "Assembly", "Packing", "Dispatch"],
    index=0
)

priority_filter = st.sidebar.selectbox(
    "Priority",
    ["All", "High", "Medium", "Low"],
    index=0
)

product_filter = st.sidebar.selectbox(
    "Product Type",
    ["All", "Bag", "Box"],
    index=0
)

sort_by = st.sidebar.selectbox(
    "Sort By",
    ["Newest First", "Oldest First", "Priority"],
    index=0
)

# ---------------- FILTER LOGIC ----------------
def matches_search(o):
    if not search:
        return True
    s = search.lower()
    return (
        s in o.get("order_id", "").lower() or
        s in o.get("customer", "").lower() or
        s in o.get("item", "").lower()
    )

filtered_orders = []

for key, o in orders.items():
    if not isinstance(o, dict):
        continue

    # Stage filter
    if stage_filter != "All" and o.get("stage") != stage_filter:
        continue

    # Priority filter
    if priority_filter != "All" and o.get("priority") != priority_filter:
        continue

    # Product type filter
    if product_filter != "All" and o.get("product_type") != product_filter:
        continue

    # Search filter
    if not matches_search(o):
        continue

    filtered_orders.append((key, o))

# -------- SORTING --------
if sort_by == "Newest First":
    filtered_orders.sort(key=lambda x: x[1].get("received", ""), reverse=True)
elif sort_by == "Oldest First":
    filtered_orders.sort(key=lambda x: x[1].get("received", ""))
elif sort_by == "Priority":
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    filtered_orders.sort(key=lambda x: priority_rank.get(x[1].get("priority", "Medium"), 1))

# ------------------- FILE PREVIEW FUNCTION -------------------
def preview_file(b64data):
    if not b64data:
        st.warning("No file uploaded.")
        return

    raw = base64.b64decode(b64data)
    head = raw[:10]

    if head.startswith(b"%PDF"):
        st.info("PDF file — download to view.")
    elif head.startswith(b"\x89PNG") or head[:3] == b"\xff\xd8\xff":
        st.image(raw, use_container_width=True)
    else:
        st.info("Unknown file format.")

# ---------------- DISPLAY RESULTS ----------------
st.subheader(f"📦 Showing {len(filtered_orders)} orders")

if not filtered_orders:
    st.warning("No orders match your filters.")
    st.stop()

for key, o in filtered_orders:
    with st.container(border=True):

        col1, col2, col3, col4 = st.columns([2,2,2,2])

        # Basic info
        col1.markdown(f"### 🏷 Order **{o.get('order_id')}**")
        col1.caption(f"Customer: **{o.get('customer')}**")

        col2.metric("Priority", o.get("priority", "—"))
        col3.metric("Product Type", o.get("product_type", "—"))
        col4.metric("Stage", o.get("stage", "—"))

        st.markdown("---")

        # Timeline
        c1, c2, c3 = st.columns(3)
        c1.write(f"📥 Received: **{o.get('received','')}**")
        c2.write(f"📅 Due: **{o.get('due','')}**")

        # STATUS COLOR
        if o.get("stage") == "Dispatch":
            c3.success("Completed & Dispatched")
        else:
            c3.info(f"Current Stage: **{o.get('stage')}**")

        st.markdown("---")

        # Full ORDER DETAILS DROP-DOWN
        with st.expander("📋 View Full Order Details"):
            st.json(o)

        # ---------------- FILE CHECK IN EVERY STAGE ----------------
        st.markdown("### 📁 Attached Files")

        colA, colB, colC, colD = st.columns(4)

        # Design Final File
        if o.get("design_files",{}).get("final"):
            with colA:
                st.markdown("**Design Final Art**")
                preview_file(o["design_files"]["final"])
                st.download_button(
                    "Download",
                    base64.b64decode(o["design_files"]["final"]),
                    file_name=f"{o['order_id']}_design_final.pdf"
                )

        # Printing Ready File
        if o.get("print_ready_file"):
            with colB:
                st.markdown("**Print Ready File**")
                preview_file(o["print_ready_file"])
                st.download_button("Download", base64.b64decode(o["print_ready_file"]),
                                   file_name=f"{o['order_id']}_print_ready.pdf")

        # Lamination Output
        if o.get("lamination_file"):
            with colC:
                st.markdown("**Lamination File**")
                preview_file(o["lamination_file"])
                st.download_button("Download", base64.b64decode(o["lamination_file"]),
                                   file_name=f"{o['order_id']}_lamination.pdf")

        # Packing Output
        if o.get("packing_file"):
            with colD:
                st.markdown("**Packing Output**")
                preview_file(o["packing_file"])
                st.download_button(
                    "Download",
                    base64.b64decode(o["packing_file"]),
                    file_name=f"{o['order_id']}_packing_output.pdf"
                )

        st.markdown("---")

        # ------- ADMIN ONLY DELETE BUTTON --------
        if st.session_state["role"] == "admin":
            if st.button(f"🗑 Delete Order {o['order_id']}", key=f"del_{o['order_id']}"):
                update(f"orders/{key}", None)  # delete
                st.success("Deleted Successfully!")
                st.rerun()
