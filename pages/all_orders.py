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

st.title("📋 All Orders Overview Dashboard (Advanced Production Analytics)")
st.write("View and manage all orders in the system with advanced metrics, stage time analysis, and filtering.")

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

def get_stage_seconds(order, start_key, end_key):
    """Safely calculates duration in seconds between two timestamps."""
    start = order.get(start_key)
    end = order.get(end_key)
    if start and end:
        try:
            t1 = datetime.fromisoformat(start)
            t2 = datetime.fromisoformat(end)
            return (t2 - t1).total_seconds()
        except:
            return None
    return None

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

# New KPI Calculations: Cycle Time, On-Time Rate & Average Stage Times
total_cycle_time_seconds = 0
on_time_count = 0
stage_time_totals = {"Design": 0.0, "Printing": 0.0, "DieCut": 0.0, "Assembly": 0.0, "Packing": 0.0}
stage_time_counts = {"Design": 0, "Printing": 0, "DieCut": 0, "Assembly": 0, "Packing": 0}


if total_completed > 0:
    for order in completed_orders_data:
        received_str = order.get('received')
        # Use dispatched_at or packing_completed_at for the final timestamp
        completed_str = order.get('dispatched_at') or order.get('packing_completed_at') 
        due_str = order.get('due')

        # 1. Total Cycle Time & On-Time Check
        if received_str and completed_str:
            try:
                received_dt = datetime.fromisoformat(received_str)
                completed_dt = datetime.fromisoformat(completed_str)
                total_cycle_time_seconds += (completed_dt - received_dt).total_seconds()
                
                if due_str:
                    due_dt = datetime.fromisoformat(due_str)
                    if completed_dt <= due_dt:
                        on_time_count += 1
            except:
                pass 
        
        # 2. Individual Stage Times
        stages_map = [
            ('Design', 'started_at', 'design_completed_at'),
            ('Printing', 'printing_started_at', 'printing_completed_at'),
            ('DieCut', 'diecut_started_at', 'diecut_completed_at'),
            ('Assembly', 'assembly_started_at', 'assembly_completed_at'),
            ('Packing', 'packing_start', 'packing_completed_at'),
        ]
        
        for stage, start_key, end_key in stages_map:
            s = get_stage_seconds(order, start_key, end_key)
            if s is not None:
                stage_time_totals[stage] += s
                stage_time_counts[stage] += 1
                

    avg_cycle_time_seconds = total_cycle_time_seconds / total_completed
    avg_cycle_time = str(timedelta(seconds=avg_cycle_time_seconds)).split('.')[0]
    on_time_rate = f"{(on_time_count / total_completed) * 100:.1f}%"
    
    # Calculate Average Stage Times (H:M:S string)
    avg_stage_times = {}
    for stage, total_s in stage_time_totals.items():
        count = stage_time_counts[stage]
        if count > 0:
            avg_s = total_s / count
            avg_stage_times[stage] = str(timedelta(seconds=avg_s)).split('.')[0]
        else:
            avg_stage_times[stage] = "N/A"
            
else:
    avg_cycle_time = "N/A"
    on_time_rate = "N/A"
    avg_stage_times = {}

# Display Core KPIs
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Orders", total_orders, "Total in System")
col2.metric("Orders In Progress", in_progress_orders, "Currently Active")
col3.metric("Orders Completed", total_completed, "Finalized")
col4.metric("Avg. Cycle Time", avg_cycle_time, "Received to Final")
col5.metric("On-Time Delivery Rate", on_time_rate, f"{on_time_count} of {total_completed} on time")

st.divider()

# Visualization 1: Order Distribution
stage_counts: Dict[str, int] = {
    "Design": 0, "Printing": 0, "DieCut": 0, "Assembly": 0, 
    "Packing": 0, "Dispatch": 0, "Completed": 0
}
for o in orders.values():
    stage = o.get('stage', 'Unknown')
    if stage in stage_counts:
        stage_counts[stage] += 1

col_viz1, col_viz2 = st.columns(2)

with col_viz1:
    st.subheader("Order Count Distribution")
    chart_data = pd.DataFrame(
        list(stage_counts.items()),
        columns=['Stage', 'Count']
    )
    chart_data = chart_data.set_index('Stage')
    st.bar_chart(chart_data)

# Visualization 2: Average Stage Time
with col_viz2:
    if total_completed > 0 and any(stage_time_counts.values()):
        avg_time_chart_data = {
            'Stage': [],
            'Avg_Seconds': []
        }
        for stage, total_s in stage_time_totals.items():
            count = stage_time_counts[stage]
            if count > 0:
                avg_time_chart_data['Stage'].append(stage)
                avg_time_chart_data['Avg_Seconds'].append(total_s / count)

        avg_df = pd.DataFrame(avg_time_chart_data).set_index('Stage')
        # Convert seconds to minutes for better visualization scale
        avg_df['Avg Time (Min)'] = avg_df['Avg_Seconds'] / 60 
        
        st.subheader("Avg. Time Spent Per Stage (Completed Orders)")
        st.bar_chart(avg_df['Avg Time (Min)'])
        with st.expander("Average Stage Time Breakdown (H:M:S)"):
            st.json(avg_stage_times)
    else:
        st.info("Insufficient data for Average Stage Time analysis.")


st.divider()

# -------------------------------------
# FILTERS PANEL (Moved to Main Screen)
# -------------------------------------
with st.expander("🔍 Filter & Search Orders", expanded=False):
    
    st.markdown("##### Filter by Stage, Product, and Priority")
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

    st.markdown("---")
    
    st.markdown("##### Filter by Date Range and Text Search")
    
    # Date Filters (default 30 days)
    col_d1, col_d2, _ = st.columns([1, 1, 1])
    start_date_filter = col_d1.date_input("Start Date (Received)", value=datetime.today().date() - timedelta(days=30), key="start_date")
    end_date_filter = col_d2.date_input("End Date (Received)", value=datetime.today().date(), key="end_date")

    # Text Filters
    col_t1, col_t2, _ = st.columns([1, 1, 1])
    customer_filter = col_t1.text_input("Customer Name Search")
    order_search = col_t2.text_input("Search Order ID")


st.caption("Expand the filter box above to refine your search.")

# -------------------------------------
# APPLY FILTERS
# -------------------------------------

filtered: Dict[str, Any] = {}
# Prepare datetime objects for range comparison (start of day / end of day)
start_dt = datetime.combine(start_date_filter, datetime.min.time())
end_dt = datetime.combine(end_date_filter, datetime.max.time())

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
        
    # DATE FILTER (uses 'received' timestamp)
    received_str = o.get("received")
    if received_str:
        try:
            received_dt = datetime.fromisoformat(received_str)
            if received_dt < start_dt or received_dt > end_dt:
                continue
        except:
            # Skip if date is malformed
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
st.subheader(f"Filtered Orders: {len(filtered)} found.")

if not filtered:
    st.info("No orders match the selected filters.")
    st.stop()

# Sort by received date for better overview
sorted_filtered_list: list[Tuple[str, Any]] = sorted(
    filtered.items(),
    key=lambda x: x[1].get("received", "2099-12-31"),
    reverse=True # Show newest first
)

# --- Summary Table (New Feature) ---
summary_data = []
for key, order in sorted_filtered_list:
    stage = order.get('stage', 'N/A')
    
    total_order_cycle = ""
    if stage == 'Completed':
         total_order_cycle = calculate_stage_duration(order.get('received'), order.get('dispatched_at') or order.get('packing_completed_at'))

    summary_data.append({
        "Order ID": order.get('order_id', key),
        "Customer": order.get('customer', 'N/A'),
        "Stage": stage,
        "Priority": order.get('priority', 'N/A'),
        "Product Type": order.get('product_type', 'N/A'),
        "Quantity": order.get('qty', 'N/A'),
        "Received": order.get('received', 'N/A').split('T')[0],
        "Due Date": order.get('due', 'N/A').split('T')[0],
        "Total Cycle Time": total_order_cycle if stage == 'Completed' else 'In Progress',
    })

summary_df = pd.DataFrame(summary_data)
st.markdown("#### High-Level Order Summary")
st.dataframe(
    summary_df, 
    use_container_width=True, 
    hide_index=True,
    column_config={
        "Total Cycle Time": st.column_config.TextColumn(
            "Total Cycle Time",
            help="Time from order received to final completion/dispatch."
        )
    }
)

st.divider()
st.subheader("Individual Order Details")

for key, order in sorted_filtered_list:
    
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
