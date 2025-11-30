import streamlit as st
import pandas as pd
import altair as alt # Import Altair for advanced charting
from firebase import read
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List

st.set_page_config(page_title="Admin Order Overview", page_icon="📋", layout="wide")

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] != "admin":
    st.error("❌ Only admin can view this page.")
    st.stop()

st.title("📋 All Orders Overview Dashboard (Executive Production Analytics)")
st.write("Deep dive into production efficiency, performance against targets, and data quality.")

# -------------------------------------
# CONFIGURATION
# -------------------------------------
# Target KPI for comparison
ON_TIME_RATE_TARGET = 85.0 # Target 85% On-Time Delivery
DATA_QUALITY_TARGET = 95.0 # Target 95% Data Quality

# Define all possible production stages with their start/end keys
PRODUCTION_STAGES = [
    ('Design', 'started_at', 'design_completed_at'),
    ('Printing', 'printing_started_at', 'printing_completed_at'),
    ('DieCut', 'diecut_started_at', 'diecut_completed_at'),
    ('Assembly', 'assembly_started_at', 'assembly_completed_at'),
    ('Packing', 'packing_start', 'packing_completed_at'),
]

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

def format_seconds_to_hms(seconds: float) -> str:
    """Converts a duration in seconds to a H:M:S string format."""
    return str(timedelta(seconds=seconds)).split('.')[0]

def analyze_kpis(data_list: List[Dict[str, Any]]):
    """Calculates Cycle Time, On-Time Rate, and Avg Stage Times for a given list of orders."""
    total_cycle_time_seconds = 0
    on_time_count = 0
    
    stage_time_totals = {stage[0]: 0.0 for stage in PRODUCTION_STAGES}
    stage_time_counts = {stage[0]: 0 for stage in PRODUCTION_STAGES}
    stage_performance = {stage[0]: {'fastest': (float('inf'), None), 'slowest': (0.0, None)} for stage in PRODUCTION_STAGES}

    completed_orders = [o for o in data_list if o.get('stage') == 'Completed']
    completed_count = len(completed_orders)

    if completed_count > 0:
        for order in completed_orders:
            received_str = order.get('received')
            completed_str = order.get('dispatched_at') or order.get('packing_completed_at') 
            due_str = order.get('due')
            order_id = order.get('order_id', 'Unknown')

            # 1. Total Cycle Time & On-Time Check
            if received_str and completed_str:
                try:
                    received_dt = datetime.fromisoformat(received_str)
                    completed_dt = datetime.fromisoformat(completed_str)
                    cycle_time_seconds = (completed_dt - received_dt).total_seconds()
                    total_cycle_time_seconds += cycle_time_seconds
                    
                    if due_str:
                        due_dt = datetime.fromisoformat(due_str)
                        if completed_dt <= due_dt:
                            on_time_count += 1
                except:
                    pass 
            
            # 2. Individual Stage Times & Performance Tracking
            for stage, start_key, end_key in PRODUCTION_STAGES:
                s = get_stage_seconds(order, start_key, end_key)
                if s is not None:
                    stage_time_totals[stage] += s
                    stage_time_counts[stage] += 1
                    
                    # Track fastest/slowest
                    if s < stage_performance[stage]['fastest'][0]:
                        stage_performance[stage]['fastest'] = (s, order_id)
                    if s > stage_performance[stage]['slowest'][0]:
                        stage_performance[stage]['slowest'] = (s, order_id)

        avg_cycle_time_seconds = total_cycle_time_seconds / completed_count
        avg_cycle_time = format_seconds_to_hms(avg_cycle_time_seconds)
        on_time_rate = (on_time_count / completed_count) * 100
        
        # Calculate Average Stage Times (H:M:S string)
        avg_stage_times = {}
        for stage, total_s in stage_time_totals.items():
            count = stage_time_counts[stage]
            if count > 0:
                avg_stage_times[stage] = format_seconds_to_hms(total_s / count)
            else:
                avg_stage_times[stage] = "N/A"
                
    else:
        avg_cycle_time = "N/A"
        on_time_rate = 0.0
        avg_stage_times = {}
        
    return {
        "completed_count": completed_count,
        "on_time_count": on_time_count,
        "avg_cycle_time": avg_cycle_time,
        "on_time_rate": on_time_rate,
        "avg_stage_times": avg_stage_times,
        "stage_time_totals": stage_time_totals,
        "stage_time_counts": stage_time_counts,
        "stage_performance": stage_performance,
    }


# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders: Dict[str, Any] = read("orders") or {}

if not orders or not isinstance(orders, dict):
    st.warning("No orders found.")
    st.stop()

all_orders_list = list(orders.values())
total_orders = len(all_orders_list)
overall_kpis = analyze_kpis(all_orders_list)


# -------------------------------------
# KPI & DATA QUALITY METRICS
# -------------------------------------

# Data Quality Check (Rerun from pages/all_orders logic for consistency)
missing_data_count = 0
for o in all_orders_list:
    # Use a defined set of critical keys (can be expanded)
    critical_keys = ['received', 'due', 'customer', 'qty', 'item']
    if any(not o.get(k) for k in critical_keys):
        missing_data_count += 1

data_quality_score = (1 - (missing_data_count / total_orders)) * 100 if total_orders > 0 else 0.0
data_quality_percent = f"{data_quality_score:.1f}%"
data_quality_delta = f"{data_quality_score - DATA_QUALITY_TARGET:.1f}% vs Target"

# SLA Violation Count (using a 7-day/168h SLA)
sla_violation_count = 0
for o in overall_kpis['completed_orders']: # Need completed orders list here, but it's not exposed directly from analyze_kpis
    # Re-calculate completed orders list temporarily
    received_str = o.get('received')
    completed_str = o.get('dispatched_at') or o.get('packing_completed_at') 
    
    if received_str and completed_str:
        try:
            received_dt = datetime.fromisoformat(received_str)
            completed_dt = datetime.fromisoformat(completed_str)
            cycle_time_hours = (completed_dt - received_dt).total_seconds() / 3600
            if cycle_time_hours > 168:
                sla_violation_count += 1
        except:
            pass # Skip orders with time errors

# Calculate a weighted Efficiency Score (e.g., 70% OTD + 30% DQ)
efficiency_score = (overall_kpis['on_time_rate'] * 0.7) + (data_quality_score * 0.3)


# -------------------------------------
# KPI COMPARISON AND DISPLAY
# -------------------------------------

on_time_rate = overall_kpis['on_time_rate']
on_time_delta = f"{on_time_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Total Orders", total_orders, "Total in System")
col2.metric("Orders Completed", overall_kpis['completed_count'], "Total Finished")
col3.metric(
    "Efficiency Score (WIP)", 
    f"{efficiency_score:.1f}", 
    help="Weighted Score: 70% OTD Rate + 30% Data Quality"
)
col4.metric(
    "On-Time Delivery Rate", 
    f"{on_time_rate:.1f}%", 
    delta=on_time_delta, 
    delta_color="normal" if on_time_rate >= ON_TIME_RATE_TARGET else "inverse"
)
col5.metric(
    "SLA Violation Count",
    sla_violation_count,
    delta="Completed orders exceeding 7 days",
    delta_color="inverse" if sla_violation_count > 0 else "normal"
)
col6.metric(
    "Data Quality Score", 
    data_quality_percent, 
    delta=data_quality_delta, 
    delta_color="normal" if data_quality_score >= DATA_QUALITY_TARGET else "inverse"
)

st.divider()

# -------------------------------------
# SEGMENTED KPI ANALYSIS BY PRODUCT TYPE
# -------------------------------------
st.subheader("Segmented Performance Analysis")

bag_orders = [o for o in all_orders_list if o.get('product_type') == 'Bag']
box_orders = [o for o in all_orders_list if o.get('product_type') == 'Box']

bag_kpis = analyze_kpis(bag_orders)
box_kpis = analyze_kpis(box_orders)

col_seg1, col_seg2 = st.columns(2)

# Bag Segment
with col_seg1:
    st.markdown("#### Product Type: Bag")
    if bag_kpis['completed_count'] > 0:
        bag_rate = bag_kpis['on_time_rate']
        bag_delta = f"{bag_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"
        
        st.metric(
            "OTD Rate (Bags)", 
            f"{bag_rate:.1f}%", 
            delta=bag_delta,
            delta_color="normal" if bag_rate >= ON_TIME_RATE_TARGET else "inverse"
        )
        st.markdown(f"**Avg. Cycle Time:** {bag_kpis['avg_cycle_time']}")
        st.caption(f"{bag_kpis['completed_count']} completed orders analyzed.")
        with st.expander("Bag Stage Time Breakdown"):
            st.json(bag_kpis['avg_stage_times'])
    else:
        st.info("No completed 'Bag' orders for analysis.")

# Box Segment
with col_seg2:
    st.markdown("#### Product Type: Box")
    if box_kpis['completed_count'] > 0:
        box_rate = box_kpis['on_time_rate']
        box_delta = f"{box_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"
        
        st.metric(
            "OTD Rate (Boxes)", 
            f"{box_rate:.1f}%", 
            delta=box_delta,
            delta_color="normal" if box_rate >= ON_TIME_RATE_TARGET else "inverse"
        )
        st.markdown(f"**Avg. Cycle Time:** {box_kpis['avg_cycle_time']}")
        st.caption(f"{box_kpis['completed_count']} completed orders analyzed.")
        with st.expander("Box Stage Time Breakdown"):
            st.json(box_kpis['avg_stage_times'])
    else:
        st.info("No completed 'Box' orders for analysis.")

st.divider()

# -------------------------------------
# BOTTLENECK & STAGE PERFORMANCE ANALYSIS
# -------------------------------------
st.subheader("Bottleneck and Stage Performance ")

avg_stage_times_seconds = {}
for stage, total_s in overall_kpis['stage_time_totals'].items():
    count = overall_kpis['stage_time_counts'].get(stage, 0)
    if count > 0:
        avg_stage_times_seconds[stage] = total_s / count

if avg_stage_times_seconds:
    # 3. Bottleneck Detection
    bottleneck_stage = max(avg_stage_times_seconds, key=avg_stage_times_seconds.get)
    bottleneck_time = format_seconds_to_hms(avg_stage_times_seconds[bottleneck_stage])
    
    st.markdown(f"### 🛑 Current Bottleneck: **{bottleneck_stage}**")
    st.markdown(f"The **{bottleneck_stage}** stage has the highest average duration: **{bottleneck_time}**.")

    st.markdown("---")
    
    # 4. Fastest & Slowest Orders (Top Delays)
    st.markdown("### Top Delays and Exceptional Performance (Fastest/Slowest Orders)")
    
    performance_table = []
    for stage in PRODUCTION_STAGES:
        stage_name = stage[0]
        perf = overall_kpis['stage_performance'][stage_name]
        
        fastest_s, fastest_id = perf['fastest']
        slowest_s, slowest_id = perf['slowest']
        
        # Only show stages with recorded data
        if overall_kpis['stage_time_counts'][stage_name] > 0:
            performance_table.append({
                "Stage": stage_name,
                "Fastest Time": format_seconds_to_hms(fastest_s) if fastest_s != float('inf') else "N/A",
                "Fastest Order": fastest_id or "N/A",
                "Slowest Time (Delay)": format_seconds_to_hms(slowest_s) if slowest_s > 0 else "N/A",
                "Slowest Order": slowest_id or "N/A",
                "Total Orders Analyzed": overall_kpis['stage_time_counts'][stage_name]
            })

    st.dataframe(pd.DataFrame(performance_table), use_container_width=True, hide_index=True)


st.divider()

# -------------------------------------
# VISUALIZATIONS
# -------------------------------------

col_viz1, col_viz2 = st.columns(2)

with col_viz1:
    st.subheader("Order Count Distribution")
    stage_counts: Dict[str, int] = {
        "Design": 0, "Printing": 0, "DieCut": 0, "Assembly": 0, 
        "Packing": 0, "Dispatch": 0, "Completed": 0
    }
    for o in orders.values():
        stage = o.get('stage', 'Unknown')
        if stage in stage_counts:
            stage_counts[stage] += 1
            
    chart_data = pd.DataFrame(
        list(stage_counts.items()),
        columns=['Stage', 'Count']
    )
    chart_data = chart_data.set_index('Stage')
    st.bar_chart(chart_data)

# Visualization 2: Average Stage Time / Delay Heat-Map
with col_viz2:
    if overall_kpis['completed_count'] > 0 and any(overall_kpis['stage_time_counts'].values()):
        
        avg_time_chart_data = []
        for stage, total_s in overall_kpis['stage_time_totals'].items():
            count = overall_kpis['stage_time_counts'][stage]
            if count > 0:
                avg_time_chart_data.append({
                    'Stage': stage,
                    # Convert seconds to minutes for better visualization scale
                    'Avg Time (Min)': (total_s / count) / 60 
                })

        avg_df = pd.DataFrame(avg_time_chart_data)
        
        st.subheader("Avg. Time Spent Per Stage (Delay Heat-Map)")
        
        # Create Altair Heatmap/Bar chart where color represents the time
        chart = alt.Chart(avg_df).mark_bar().encode(
            x=alt.X('Stage', sort=list(avg_stage_times_seconds.keys())),
            y=alt.Y('Avg Time (Min)', title='Average Duration (Minutes)'),
            color=alt.Color('Avg Time (Min)', scale=alt.Scale(range='heatmap', domain=[avg_df['Avg Time (Min)'].min(), avg_df['Avg Time (Min)'].max()])),
            tooltip=['Stage', alt.Tooltip('Avg Time (Min)', format='.2f')]
        ).properties(
            title="Stage Time Breakdown (Highest time is the Bottleneck)"
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Insufficient data for Average Stage Time analysis.")


st.divider()

# -------------------------------------
# FILTERS PANEL (Moved to Main Screen)
# -------------------------------------

# Quick Filters for immediate action
st.markdown("#### Quick Action Filters")
col_q1, col_q2, col_q3 = st.columns(3)
quick_filter = col_q1.selectbox(
    "Quick Filter Set",
    ["None", "Late or Past Due", "High Priority Active", "Data Quality Issues"]
)

# Standard Filters (in expander)
with st.expander("🔍 Advanced Filter & Search Orders", expanded=False):
    
    st.markdown("##### Filter by Stage, Product, and Priority")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    stage_filter = col_s1.selectbox(
        "Stage",
        ["All", "Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"],
        key="stage_f"
    )
    
    product_filter = col_s2.selectbox(
        "Product Type",
        ["All", "Bag", "Box"],
        key="product_f"
    )
    
    priority_filter = col_s3.selectbox(
        "Priority",
        ["All", "High", "Medium", "Low"],
        key="priority_f"
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
start_dt = datetime.combine(start_date_filter, datetime.min.time())
end_dt = datetime.combine(end_date_filter, datetime.max.time())
now = datetime.now()

for key, o in orders.items():

    if not isinstance(o, dict):
        continue
    
    # --- QUICK FILTERS ---
    if quick_filter == "Late or Past Due":
        due_str = o.get('due')
        completed_str = o.get('dispatched_at') or o.get('packing_completed_at')
        is_completed = o.get('stage') == 'Completed'
        is_late = False

        if due_str:
            try:
                due_dt = datetime.fromisoformat(due_str)
                
                if is_completed and completed_str:
                    # Completed late
                    if datetime.fromisoformat(completed_str) > due_dt:
                        is_late = True
                elif not is_completed:
                    # In progress and past due date
                    if now > due_dt:
                        is_late = True
            except:
                pass 
        
        if not is_late:
            continue
            
    elif quick_filter == "High Priority Active":
        if o.get('priority') != 'High' or o.get('stage') == 'Completed':
            continue

    elif quick_filter == "Data Quality Issues":
        # Check for any critical key missing (same logic as used for KPI calculation)
        critical_keys = ['received', 'due', 'customer', 'qty', 'item']
        if not any(not o.get(k) for k in critical_keys):
            continue
            
    # --- STANDARD FILTERS ---
    if stage_filter != "All" and o.get("stage") != stage_filter:
        continue

    if product_filter != "All" and o.get("product_type") != product_filter:
        continue

    if priority_filter != "All" and o.get("priority") != priority_filter:
        continue
        
    received_str = o.get("received")
    if received_str:
        try:
            received_dt = datetime.fromisoformat(received_str)
            if received_dt < start_dt or received_dt > end_dt:
                continue
        except:
            continue 

    if customer_filter and customer_filter.lower() not in o.get("customer", "").lower():
        continue

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

# --- Summary Table ---
summary_data = []
for key, order in sorted_filtered_list:
    stage = order.get('stage', 'N/A')
    
    total_order_cycle = ""
    is_late_indicator = "🟢 On Time"
    
    due_dt_raw = order.get('due')
    
    if due_dt_raw:
        try:
            due_dt = datetime.fromisoformat(due_dt_raw)
            if stage == 'Completed':
                completed_str = order.get('dispatched_at') or order.get('packing_completed_at')
                if completed_str and datetime.fromisoformat(completed_str) > due_dt:
                    is_late_indicator = "🔴 Late"
            elif datetime.now() > due_dt:
                is_late_indicator = "🟠 Past Due"
        except:
            is_late_indicator = "🟡 Due Date Error"

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
        "Status": is_late_indicator,
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
