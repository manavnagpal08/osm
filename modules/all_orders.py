import streamlit as st
import pandas as pd
import altair as alt # Import Altair for advanced charting
from firebase import read
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Admin Order Overview", page_icon="📋", layout="wide")

# -------------------------------------
# ROLE CHECK & PAGE SETUP
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
# Critical keys for Data Quality check
CRITICAL_DATA_KEYS = ['received', 'due', 'customer', 'qty', 'item', 'product_type', 'priority']

# -------------------------------------
# UTILITY FUNCTIONS (Enhanced)
# -------------------------------------

@st.cache_data(ttl=600) # Cache the KPI results for 10 minutes
def format_seconds_to_hms(seconds: float) -> str:
    """Converts a duration in seconds to a H:M:S string format."""
    # Use timedelta for robust formatting
    return str(timedelta(seconds=seconds)).split('.')[0]

@st.cache_data(ttl=600) # Cache function execution to speed up dashboard loading
def get_stage_seconds(order: Dict[str, Any], start_key: str, end_key: str) -> Optional[float]:
    """Safely calculates duration in seconds between two ISO timestamps."""
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

def calculate_stage_duration(start_time: Optional[str], end_time: Optional[str]) -> str:
    """Calculates the duration between two ISO format timestamps and returns H:M:S."""
    if start_time and end_time:
        try:
            diff_seconds = get_stage_seconds({'start': start_time, 'end': end_time}, 'start', 'end')
            if diff_seconds is not None:
                 return f"**{format_seconds_to_hms(diff_seconds)}**"
        except:
            return "N/A (Time Error)"
    return "In Progress"

# NOTE: The get_completion_info and analyze_kpis functions are kept largely the same
# but now use the optimized/cached helper functions where possible.

def get_completion_info(stage: str) -> Tuple[float, str]:
    """Returns progress percentage and status color based on stage."""
    stages = ["Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"]
    if stage == 'Completed':
        return 1.0, "green"
    try:
        index = stages.index(stage)
        progress = (index + 0.5) / len(stages) 
        color = "blue"
        if stage in ["Packing", "Dispatch"]:
            color = "orange"
        return progress, color
    except ValueError:
        return 0.05, "gray"

@st.cache_data(ttl=600) # Crucial: Cache the expensive KPI calculation
def analyze_kpis(data_list: List[Dict[str, Any]]):
    """
    Calculates key production metrics, including Cycle Time, On-Time Rate,
    and Avg Stage Times for a given list of orders.
    """
    total_cycle_time_seconds = 0
    on_time_count = 0
    
    stage_time_totals = {stage[0]: 0.0 for stage in PRODUCTION_STAGES}
    stage_time_counts = {stage[0]: 0 for stage in PRODUCTION_STAGES}
    stage_performance = {stage[0]: {'fastest': (float('inf'), None), 'slowest': (0.0, None)} for stage in PRODUCTION_STAGES}

    completed_orders = [o for o in data_list if o.get('stage') == 'Completed']
    completed_count = len(completed_orders)
    
    # NEW: Data quality tracking per key
    data_quality_breakdown = {key: 0 for key in CRITICAL_DATA_KEYS}
    
    total_orders = len(data_list)
    missing_data_count = 0
    
    for order in data_list:
        order_id = order.get('order_id', 'Unknown')
        
        # Data Quality Check
        has_missing = False
        for k in CRITICAL_DATA_KEYS:
            if not order.get(k):
                data_quality_breakdown[k] += 1
                has_missing = True
        if has_missing:
            missing_data_count += 1

        if order.get('stage') == 'Completed':
            # 1. Total Cycle Time & On-Time Check (Only for completed orders)
            received_str = order.get('received')
            completed_str = order.get('dispatched_at') or order.get('packing_completed_at')
            due_str = order.get('due')

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

    if completed_count > 0:
        avg_cycle_time_seconds = total_cycle_time_seconds / completed_count
        avg_cycle_time = format_seconds_to_hms(avg_cycle_time_seconds)
        on_time_rate = (on_time_count / completed_count) * 100
        
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
        
    data_quality_score = (1 - (missing_data_count / total_orders)) * 100 if total_orders > 0 else 0.0

    return {
        "completed_count": completed_count,
        "completed_orders": completed_orders,
        "on_time_count": on_time_count,
        "avg_cycle_time": avg_cycle_time,
        "on_time_rate": on_time_rate,
        "avg_stage_times": avg_stage_times,
        "stage_time_totals": stage_time_totals,
        "stage_time_counts": stage_time_counts,
        "stage_performance": stage_performance,
        "data_quality_score": data_quality_score,
        "data_quality_breakdown": data_quality_breakdown, # New metric
        "total_orders": total_orders
    }

# -------------------------------------
# FETCH & PRE-ANALYZE ORDERS
# -------------------------------------
@st.cache_data(ttl=600)
def fetch_and_analyze_data():
    """Fetches data and runs the initial, cached KPI analysis."""
    orders: Dict[str, Any] = read("orders") or {}
    if not orders or not isinstance(orders, dict):
        return None, None, 0
    
    all_orders_list = list(orders.values())
    overall_kpis = analyze_kpis(all_orders_list)
    return orders, all_orders_list, overall_kpis

orders, all_orders_list, overall_kpis = fetch_and_analyze_data()

if not orders:
    st.warning("No orders found or data fetching failed.")
    st.stop()

total_orders = len(all_orders_list)
on_time_rate = overall_kpis['on_time_rate']
data_quality_score = overall_kpis['data_quality_score']
on_time_delta = f"{on_time_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"
data_quality_percent = f"{data_quality_score:.1f}%"
data_quality_delta = f"{data_quality_score - DATA_QUALITY_TARGET:.1f}% vs Target"

# SLA Violation Count (Moved outside of the cached analyze_kpis for simplicity)
sla_violation_count = 0
for o in overall_kpis['completed_orders']: 
    received_str = o.get('received')
    completed_str = o.get('dispatched_at') or o.get('packing_completed_at') 
    
    if received_str and completed_str:
        try:
            received_dt = datetime.fromisoformat(received_str)
            completed_dt = datetime.fromisoformat(completed_str)
            cycle_time_hours = (completed_dt - received_dt).total_seconds() / 3600
            if cycle_time_hours > 168: # 7 days = 168 hours
                sla_violation_count += 1
        except:
            pass 

# Calculate a weighted Efficiency Score
efficiency_score = (on_time_rate * 0.7) + (data_quality_score * 0.3)


# -------------------------------------
# KPI COMPARISON AND DISPLAY (Improved Layout)
# -------------------------------------

st.subheader("📊 Executive Summary KPIs")
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
# DATA QUALITY BREAKDOWN VISUALIZATION (NEW Feature)
# -------------------------------------

st.subheader("🧹 Data Quality Audit: Missing Critical Data")

dq_df = pd.DataFrame(
    overall_kpis['data_quality_breakdown'].items(),
    columns=['Critical Field', 'Missing Count']
)

# Calculate percentage missing
dq_df['Missing %'] = (dq_df['Missing Count'] / total_orders) * 100
dq_df['Total Orders'] = total_orders

# Altair chart for Data Quality
dq_chart = alt.Chart(dq_df).mark_bar().encode(
    x=alt.X('Missing Count', title='Number of Orders Missing Data'),
    y=alt.Y('Critical Field', sort='x', title='Required Field'),
    tooltip=['Critical Field', 'Missing Count', alt.Tooltip('Missing %', format='.1f')],
    color=alt.Color('Missing %', scale=alt.Scale(range=['green', 'red'], domain=[0, max(dq_df['Missing %'].max() * 1.5, 10)]), legend=None)
).properties(
    title="Count of Orders Missing Critical Data Fields"
)

st.altair_chart(dq_chart, use_container_width=True)


st.divider()


# -------------------------------------
# BOTTLENECK & STAGE PERFORMANCE ANALYSIS
# -------------------------------------
st.subheader("⚙️ Bottleneck and Stage Performance ")

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

# Order Count Distribution (Updated with Dataframe for better Altair integration)
with col_viz1:
    st.subheader("Order Count Distribution by Stage")
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
    
    chart_data['Order'] = 1 # Dummy variable for stacking/hover
    
    # Altair bar chart with proper sorting
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('Stage', sort=list(stage_counts.keys())),
        y=alt.Y('Count', title='Number of Orders in Stage'),
        tooltip=['Stage', 'Count'],
        color=alt.Color('Stage')
    ).properties(
        title="Orders in Production Stages"
    )
    st.altair_chart(chart, use_container_width=True)

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
        
        # Create Altair Bar chart where color represents the time
        chart = alt.Chart(avg_df).mark_bar().encode(
            x=alt.X('Stage', sort=list(avg_stage_times_seconds.keys())),
            y=alt.Y('Avg Time (Min)', title='Average Duration (Minutes)'),
            # Use 'yelloworange-red' for a clear heat map
            color=alt.Color('Avg Time (Min)', scale=alt.Scale(range='yelloworange-red'), legend=alt.Legend(title="Avg Time (Min)")),
            tooltip=['Stage', alt.Tooltip('Avg Time (Min)', format='.2f')]
        ).properties(
            title="Stage Time Breakdown (Highest time is the Bottleneck)"
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Insufficient data for Average Stage Time analysis.")

st.divider()

# -------------------------------------
# FILTERS PANEL (Improved)
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
    
    # Dynamically find all unique values for product type and priority
    product_types = sorted(list(set(o.get('product_type') for o in all_orders_list if o.get('product_type'))))
    priorities = sorted(list(set(o.get('priority') for o in all_orders_list if o.get('priority'))))

    stage_filter = col_s1.selectbox(
        "Stage",
        ["All", "Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"],
        key="stage_f"
    )
    
    product_filter = col_s2.selectbox(
        "Product Type",
        ["All"] + product_types,
        key="product_f"
    )
    
    priority_filter = col_s3.selectbox(
        "Priority",
        ["All"] + priorities,
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
data_quality_keys = CRITICAL_DATA_KEYS # Use the centralized list

for key, o in orders.items():

    if not isinstance(o, dict):
        continue
    
    # --- QUICK FILTERS ---
    is_late_or_past_due = False
    due_str = o.get('due')
    completed_str = o.get('dispatched_at') or o.get('packing_completed_at')
    is_completed = o.get('stage') == 'Completed'
    
    if due_str:
        try:
            due_dt = datetime.fromisoformat(due_str)
            if (is_completed and completed_str and datetime.fromisoformat(completed_str) > due_dt) or \
               (not is_completed and now > due_dt):
                is_late_or_past_due = True
        except:
            pass 
            
    if quick_filter == "Late or Past Due" and not is_late_or_past_due:
        continue
            
    elif quick_filter == "High Priority Active" and (o.get('priority') != 'High' or is_completed):
        continue

    elif quick_filter == "Data Quality Issues" and not any(not o.get(k) for k in data_quality_keys):
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
# DISPLAY RESULTS & DOWNLOAD BUTTON (NEW Feature)
# -------------------------------------
st.subheader(f"✅ Filtered Orders: {len(filtered)} found.")

if not filtered:
    st.info("No orders match the selected filters.")
    # Show the delete button only if there are no filters applied or if the user is certain (moved to dedicated section)
else:
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
        
        is_late_indicator = "🟢 On Time"
        due_dt_raw = order.get('due')
        total_order_cycle = 'In Progress'

        # Recalculate late status and cycle time using the improved logic
        if due_dt_raw:
            try:
                due_dt = datetime.fromisoformat(due_dt_raw)
                completed_str = order.get('dispatched_at') or order.get('packing_completed_at')
                
                if stage == 'Completed' and completed_str:
                    completed_dt = datetime.fromisoformat(completed_str)
                    total_order_cycle = calculate_stage_duration(order.get('received'), completed_str)
                    if completed_dt > due_dt:
                        is_late_indicator = "🔴 Late"
                elif datetime.now() > due_dt:
                    is_late_indicator = "🟠 Past Due"
            except:
                is_late_indicator = "🟡 Due Date Error"

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
            "Total Cycle Time": total_order_cycle,
        })

    summary_df = pd.DataFrame(summary_data)
    
    st.markdown("#### High-Level Order Summary")
    
    col_sum_1, col_sum_2 = st.columns([3, 1])
    
    with col_sum_2:
        # ADDED: Download Report Button
        csv_report = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Filtered Report (CSV)",
            data=csv_report,
            file_name=f'filtered_orders_report_{datetime.now().strftime("%Y%m%d")}.csv',
            mime='text/csv',
            help="Download the currently visible table as a CSV file."
        )

    with col_sum_1:
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

    # [REMAINDER OF ORIGINAL CODE FOR INDIVIDUAL ORDER DISPLAY]
    for key, order in sorted_filtered_list:
        
        stage = order.get('stage', 'N/A')
        progress, _ = get_completion_info(stage)

        # Calculate total cycle time for the order being viewed (if completed)
        total_order_cycle = ""
        if stage == 'Completed':
            total_order_cycle = calculate_stage_duration(order.get('received'), order.get('dispatched_at') or order.get('packing_completed_at'))
            
        # Expander Header
        expander_header = f"**{order['order_id']}** — {order.get('customer', 'N/A')} | **Stage:** `{stage}`"
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

    st.divider()
    
    # -------------------------------------
    # DANGER ZONE (Delete All Orders)
    # -------------------------------------
    st.subheader("⚠️ Danger Zone: Administrative Actions")
    
    if st.session_state["role"] == "admin":
        st.warning("This action will **PERMANENTLY DELETE ALL ORDERS** in your database. Use with extreme caution.")
        delete_col, _ = st.columns([1, 4])
        
        with delete_col:
            delete_confirmation = st.checkbox("I understand and want to permanently delete ALL orders.")
            
            if delete_confirmation:
                if st.button("🔴 Permanently Delete ALL Orders", type="primary"):
                    st.error("Functionality requires 'write' access and a specific Firebase write operation which is NOT included in this code for safety. The action would execute Firebase's `delete('orders')` if implemented.")
                    # Placeholder for actual delete operation
                    # from firebase import delete
                    # delete("orders") 
                    # st.success("✅ All orders deleted successfully. Refreshing page...")
                    # st.cache_data.clear() # Clear cache after delete
                    # st.rerun()
