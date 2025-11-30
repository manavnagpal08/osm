import streamlit as st
from firebase import read
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

st.set_page_config(page_title="Admin Order Overview", page_icon="📋", layout="wide")

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] != "admin":
    st.error("❌ Only admin can view this page.")
    st.stop()

st.title("📋 All Orders Overview")
st.write("View and manage all orders in the system with advanced metrics.")

# -------------------------------------
# UTILITY FUNCTIONS
# -------------------------------------

def calculate_stage_duration(start_time: str, end_time: str) -> str:
    """Calculates the duration between two ISO format timestamps and returns H:M:S."""
    if start_time and end_time:
        try:
            t1 = datetime.fromisoformat(start_time)
            t2 = datetime.fromisoformat(end_time)
            diff = t2 - t1
            total_seconds = int(diff.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"**{hours:02}h {minutes:02}m {seconds:02}s**"
        except:
            return "N/A (Time Error)"
    return "In Progress"

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders: Dict[str, Any] = read("orders") or {}

if not orders or not isinstance(orders, dict):
    st.warning("No orders found.")
    st.stop()

# -------------------------------------
# KPI METRICS
# -------------------------------------

total_orders = len(orders)
completed_orders = sum(1 for o in orders.values() if o.get('stage') == 'Completed')
in_progress_orders = total_orders - completed_orders

st.subheader("Key Performance Indicators")
col1, col2, col3 = st.columns(3)

col1.metric("Total Orders", total_orders, "Total in System")
col2.metric("Orders In Progress", in_progress_orders, "Currently Active")
col3.metric("Orders Completed", completed_orders, "Finalized")

st.divider()

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

filtered: Dict[str, Any] = {}

for key, o in orders.items():

    if not isinstance(o, dict):
        continue

    # STAGE FILTER
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
st.subheader(f"Filtered Orders: {len(filtered)}")

if not filtered:
    st.info("No orders match the selected filters.")
    st.stop()

# Sort by received date for better overview
sorted_filtered: list[Tuple[str, Any]] = sorted(
    filtered.items(),
    key=lambda x: x[1].get("received", "2099-12-31"),
    reverse=True # Show newest first
)

for key, order in sorted_filtered:

    with st.expander(f"**{order['order_id']}** — {order['customer']} | **Stage:** `{order.get('stage', 'N/A')}`"):

        col_meta, col_dates = st.columns([1, 1])

        with col_meta:
            st.markdown("### Order Details")
            st.write(f"**Product Type:** {order.get('product_type', 'N/A')}")
            st.write(f"**Priority:** {order.get('priority', 'N/A')}")
            st.write(f"**Item:** {order.get('item', 'N/A')}")
            st.write(f"**Quantity:** {order.get('qty', 'N/A')}")

        with col_dates:
            st.markdown("### Key Timelines")
            st.write(f"**Order Received:** {order.get('received', 'N/A').split('T')[0]}")
            st.write(f"**Due Date:** {order.get('due', 'N/A').split('T')[0]}")
            st.write(f"**Current Stage:** `{order.get('stage', 'N/A')}`")


        st.divider()

        st.markdown("### Specs")
        st.write(f"Foil ID: {order.get('foil_id', 'N/A')}")
        st.write(f"Spot UV ID: {order.get('spotuv_id', 'N/A')}")
        st.write(f"Brand Thickness: {order.get('brand_thickness_id', 'N/A')}")
        st.write(f"Paper Thickness: {order.get('paper_thickness_id', 'N/A')}")
        st.write(f"Size: {order.get('size_id', 'N/A')}")
        st.write(f"Rate: {order.get('rate', 'N/A')}")

        st.divider()

        st.markdown("### Workflow Duration & Timestamps")
        
        # Calculate durations
        design_duration = calculate_stage_duration(order.get('started_at'), order.get('design_completed_at'))
        printing_duration = calculate_stage_duration(order.get('printing_started_at'), order.get('printing_completed_at'))
        diecut_duration = calculate_stage_duration(order.get('diecut_started_at'), order.get('diecut_completed_at'))
        assembly_duration = calculate_stage_duration(order.get('assembly_started_at'), order.get('assembly_completed_at'))
        packing_duration = calculate_stage_duration(order.get('packing_start'), order.get('packing_completed_at'))

        col_duration, col_timestamps = st.columns(2)

        with col_duration:
            st.markdown("#### Stage Durations")
            st.markdown(f"**Design:** {design_duration}")
            st.markdown(f"**Printing:** {printing_duration}")
            st.markdown(f"**DieCut:** {diecut_duration}")
            st.markdown(f"**Assembly:** {assembly_duration}")
            st.markdown(f"**Packing:** {packing_duration}")

        with col_timestamps:
            st.markdown("#### Key Timestamps")
            st.json({
                "next_after_printing": order.get("next_after_printing", "N/A"),
                "design_completed": order.get("design_completed_at", "N/A"),
                "printing_completed": order.get("printing_completed_at", "N/A"),
                "diecut_completed": order.get("diecut_completed_at", "N/A"),
                "assembly_completed": order.get("assembly_completed_at", "N/A"),
                "packing_completed": order.get("packing_completed_at", "N/A"),
                "dispatched_at": order.get("dispatched_at", "N/A"),
            })
