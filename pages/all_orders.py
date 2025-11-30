import streamlit as st
from firebase import read
from datetime import datetime

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] != "admin":
    st.error("❌ Only admin can view this page.")
    st.stop()

st.title("📋 All Orders Overview")
st.write("View and manage all orders in the system.")

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders = read("orders")

if not orders or not isinstance(orders, dict):
    st.warning("No orders found.")
    st.stop()

# -------------------------------------
# FILTERS PANEL
# -------------------------------------
st.sidebar.header("🔍 Filters")

stage_filter = st.sidebar.selectbox(
    "Stage",
    ["All", "Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"]
)

product_filter = st.sidebar.selectbox(
    "Product Type",
    ["All", "Bag", "Box"]
)

priority_filter = st.sidebar.selectbox(
    "Priority",
    ["All", "High", "Medium", "Low"]
)

customer_filter = st.sidebar.text_input("Customer Name Search")

order_search = st.sidebar.text_input("Search Order ID")

# -------------------------------------
# APPLY FILTERS
# -------------------------------------

filtered = {}

for key, o in orders.items():

    if not isinstance(o, dict):
        continue

    # STAGE FILTER
    # NOTE: I added 'Packing' to the filter options but also ensuring the logic here is sound
    if stage_filter != "All" and o.get("stage") != stage_filter:
        continue

    # PRODUCT TYPE FILTER
    if product_filter != "All" and o.get("product_type") != product_filter:
        continue

    # PRIORITY FILTER
    if priority_filter != "All" and o.get("priority") != priority_filter:
        continue

    # CUSTOMER FILTER
    if customer_filter and customer_filter.lower() not in o.get("customer", "").lower():
        continue

    # ORDER ID FILTER
    if order_search and order_search.lower() not in o.get("order_id", "").lower():
        continue

    filtered[key] = o

# -------------------------------------
# DISPLAY RESULTS
# -------------------------------------
st.subheader(f"Total Orders Found: {len(filtered)}")

if not filtered:
    st.info("No orders match the selected filters.")
    st.stop()

# Sort by received date for better overview
sorted_filtered = sorted(
    filtered.items(),
    key=lambda x: x[1].get("received", "2099-12-31"),
    reverse=True # Show newest first
)

for key, order in sorted_filtered:

    with st.expander(f"**{order['order_id']}** — {order['customer']} | **Stage:** `{order.get('stage', 'N/A')}`"):

        st.write(f"**Product Type:** {order.get('product_type', 'N/A')}")
        st.write(f"**Priority:** {order.get('priority', 'N/A')}")
        st.write(f"**Item:** {order.get('item', 'N/A')}")
        st.write(f"**Quantity:** {order.get('qty', 'N/A')}")

        st.write(f"**Order Received:** {order.get('received', 'N/A').split('T')[0]}")
        st.write(f"**Due Date:** {order.get('due', 'N/A').split('T')[0]}")

        st.divider()

        st.write("### Specs")
        st.write(f"Foil ID: {order.get('foil_id', 'N/A')}")
        st.write(f"Spot UV ID: {order.get('spotuv_id', 'N/A')}")
        st.write(f"Brand Thickness: {order.get('brand_thickness_id', 'N/A')}")
        st.write(f"Paper Thickness: {order.get('paper_thickness_id', 'N/A')}")
        st.write(f"Size: {order.get('size_id', 'N/A')}")
        st.write(f"Rate: {order.get('rate', 'N/A')}")

        st.divider()

        st.write("### Workflow Info (Timestamps)")
        st.json({
            "next_after_printing": order.get("next_after_printing", "N/A"),
            "design_started": order.get("started_at", "N/A"),
            "design_completed": order.get("design_completed_at", "N/A"),
            "printing_started": order.get("printing_started_at", "N/A"),
            "printing_completed": order.get("printing_completed_at", "N/A"),
            "diecut_started": order.get("diecut_started_at", "N/A"),
            "diecut_completed": order.get("diecut_completed_at", "N/A"),
            "assembly_started": order.get("assembly_started_at", "N/A"),
            "assembly_completed": order.get("assembly_completed_at", "N/A"),
            "packing_started": order.get("packing_start", "N/A"),
            "packing_completed": order.get("packing_completed_at", "N/A"),
            "dispatched_at": order.get("dispatched_at", "N/A"),
        })
