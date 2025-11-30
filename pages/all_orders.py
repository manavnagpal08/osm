import streamlit as st
import pandas as pd
from firebase import read
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

st.set_page_config(page_title="Admin Order Overview", page_icon="📋", layout="wide")

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] != "admin":
    st.error("❌ Only admin can view this page.")
    st.stop()

st.title("📋 All Orders Overview Dashboard (Advanced)")
st.write("View and manage all orders in the system with advanced metrics, analysis, and filtering.")

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

def get_completion_info(stage: str) -> Tuple[float, str]:
    """Returns progress percentage and status color based on stage."""
    stages = ["Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"]
    if stage == 'Completed':
        return 1.0, "green"
    try:
        # +0.5 to show some progress in the current stage
        index = stages.index(stage)
        progress = (index + 0.5) / len(stages) 
        color = "blue"
        if stage in ["Packing", "Dispatch"]:
            color = "orange"
        return progress, color
    except ValueError:
        return 0.05, "gray" # Show a sliver for un-categorized/new

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders: Dict[str, Any] = read("orders") or {}

if not orders or not isinstance(orders, dict):
    st.warning("No orders found.")
    st.stop()

# -------------------------------------
# KPI METRICS & VISUALIZATION
# -------------------------------------

total_orders = len(orders)
completed_orders_data = [o for o in orders.values() if o.get('stage') == 'Completed']
total_completed = len(completed_orders_data)
in_progress_orders = total_orders - total_completed

st.subheader("Key Performance Indicators")

# New KPI Calculations: Cycle Time & On-Time Rate
total_cycle_time_seconds = 0
on_time_count = 0

if total_completed > 0:
    for order in completed_orders_data:
        received_str = order.get('received')
        # Use dispatched_at or packing_completed_at for the final timestamp
        completed_str = order.get('dispatched_at') or order.get('packing_completed_at') 
        due_str = order.get('due')

        if received_str and completed_str:
            try:
                received_dt = datetime.fromisoformat(received_str)
                completed_dt = datetime.fromisoformat(completed_str)
                total_cycle_time_seconds += (completed_dt - received_dt).total_seconds()
            except:
                pass 
        
        if completed_str and due_str:
            try:
                completed_dt = datetime.fromisoformat(completed_dt)
                due_dt = datetime.fromisoformat(due_str)
                if completed_dt <= due_dt:
                    on_time_count += 1
            except:
                pass 

    avg_cycle_time_seconds = total_cycle_time_seconds / total_completed
    avg_cycle_time = str(timedelta(seconds=avg_cycle_time_seconds)).split('.')[0]
    on_time_rate = f"{(on_time_count / total_completed) * 100:.1f}%"
else:
    avg_cycle_time = "N/A"
    on_time_rate = "N/A"

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Orders", total_orders, "Total in System")
col2.metric("Orders In Progress", in_progress_orders, "Currently Active")
col3.metric("Orders Completed", total_completed, "Finalized")
col4.metric("Avg. Cycle Time", avg_cycle_time, "Received to Final")
col5.metric("On-Time Delivery Rate", on_time_rate, f"{on_time_count} of {total_completed} on time")

st.divider()

# Visualization
stage_counts: Dict[str, int] = {
    "Design": 0, "Printing": 0, "DieCut": 0, "Assembly": 0, 
    "Packing": 0, "Dispatch": 0, "Completed": 0
}
for o in orders.values():
    stage = o.get('stage', 'Unknown')
    if stage in stage_counts:
        stage_counts[stage] += 1

st.subheader("Order Distribution by Stage")
# Convert to DataFrame for better chart labels
chart_data = pd.DataFrame(
    list(stage_counts.items()),
    columns=['Stage', 'Count']
)
chart_data = chart_data.set_index('Stage')

st.bar_chart(chart_data)

st.divider()

# -------------------------------------
# FILTERS PANEL (Moved to Main Screen)
# -------------------------------------
with st.expander("🔍 Filter & Search Orders", expanded=False):
    col_s1, col_s2, col_s3 = st.columns(3)
    
    stage_filter = col_s1.selectbox(
        "Stage",
        ["All", "Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"]
    )
    
    product_filter = col_s2.selectbox(
        "Product Type",
        ["All", "Bag", "Box"]
    )
    
    priority_filter = col_s3.selectbox(
        "Priority",
        ["All", "High", "Medium", "Low"]
    )

    col_s4, col_s5 = st.columns(2)
    customer_filter = col_s4.text_input("Customer Name Search")
    order_search = col_s5.text_input("Search Order ID")

st.caption("Expand the filter box above to refine your search.")

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
    
    stage = order.get('stage', 'N/A')
    progress, _ = get_completion_info(stage)

    # Calculate total cycle time for the order being viewed (if completed)
    total_order_cycle = ""
    if stage == 'Completed':
         total_order_cycle = calculate_stage_duration(order.get('received'), order.get('dispatched_at') or order.get('packing_completed_at'))
         
    # Expander Header
    expander_header = f"**{order['order_id']}** — {order['customer']} | **Stage:** `{stage}`"
    if total_order_cycle:
        expander_header += f" | **Total Time:** {total_order_cycle}"


    with st.expander(expander_header):

        st.progress(progress, text=f"Overall Completion Progress: **{progress*100:.0f}%**")
        
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
            st.write(f"**Current Stage:** `{stage}`")


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
