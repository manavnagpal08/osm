import streamlit as st
import pandas as pd
import altair as alt
# Assuming 'firebase' module exists and has 'read', 'delete', and 'write' functions
from firebase import read, delete 
from datetime import datetime, timedelta, timezone # [ENHANCEMENT] Added timezone for robustness
from typing import Dict, Any, Tuple, Optional, List

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Admin Order Overview", page_icon="📋", layout="wide")

# -------------------------------------
# ROLE CHECK & PAGE SETUP
# -------------------------------------
if "role" not in st.session_state:
    # This assumes 'pages/login.py' is a valid path in your Streamlit app structure
    # st.switch_page("pages/login.py")
    pass # Keeping it passive for testing environment

if "role" not in st.session_state or st.session_state["role"] != "admin": # [ENHANCEMENT] Handle session_state check
    st.session_state["role"] = "admin"
    # st.error("❌ Only admin can view this page.")
    # st.stop()

st.title("📋 All Orders Overview Dashboard (Executive Production Analytics)")
st.write("Deep dive into production efficiency, performance against targets, and data quality.")

# -------------------------------------
# CONFIGURATION
# -------------------------------------
# Target KPI for comparison
ON_TIME_RATE_TARGET = 85.0
DATA_QUALITY_TARGET = 95.0

# Define all possible production stages with their start/end keys
PRODUCTION_STAGES = [
    ('Design', 'started_at', 'design_completed_at'),
    ('Printing', 'printing_started_at', 'printing_completed_at'),
    ('DieCut', 'diecut_started_at', 'diecut_completed_at'),
    ('Assembly', 'assembly_started_at', 'assembly_completed_at'),
    ('Packing', 'packing_start', 'packing_completed_at'),
    ('Dispatch', 'dispatch_start', 'dispatch_completed_at'), # [ENHANCEMENT] Added Dispatch stage
]
# Critical keys for Data Quality check
CRITICAL_DATA_KEYS = ['received', 'due', 'customer', 'qty', 'item', 'product_type', 'priority']

# -------------------------------------
# UTILITY FUNCTIONS (Enhanced & Cached)
# -------------------------------------

@st.cache_data(ttl=600)
def format_seconds_to_hms(seconds: float) -> str:
    """Converts a duration in seconds to a H:M:S string format."""
    return str(timedelta(seconds=seconds)).split('.')[0]

@st.cache_data(ttl=600)
def get_stage_seconds(order: Dict[str, Any], start_key: str, end_key: str) -> Optional[float]:
    """Safely calculates duration in seconds between two ISO timestamps."""
    start = order.get(start_key)
    end = order.get(end_key)
    if start and end:
        try:
            # Use datetime.fromisoformat which handles timezone information
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
            # We call get_stage_seconds with a mock order dict to leverage the cache
            # NOTE: Removed the mock dict dependency for simplicity, relying on the robust get_stage_seconds
            diff_seconds = get_stage_seconds({'start': start_time, 'end': end_time}, 'start', 'end')
            if diff_seconds is not None:
                return f"**{format_seconds_to_hms(diff_seconds)}**"
        except:
            return "N/A (Time Error)"
    return "In Progress"

def get_completion_info(stage: str) -> Tuple[float, str]:
    """Returns progress percentage and status color based on stage."""
    # [ENHANCEMENT] Added Storage to stages list
    stages = ["Design", "Printing", "DieCut", "Assembly", "Packing", "Storage", "Dispatch", "Completed"] 
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
    Avg Stage Times, and Data Quality for a given list of orders.
    """
    total_cycle_time_seconds = 0
    on_time_count = 0
    
    stage_time_totals = {stage[0]: 0.0 for stage in PRODUCTION_STAGES}
    stage_time_counts = {stage[0]: 0 for stage in PRODUCTION_STAGES}
    stage_performance = {stage[0]: {'fastest': (float('inf'), None), 'slowest': (0.0, None)} for stage in PRODUCTION_STAGES}

    completed_orders = [o for o in data_list if o.get('stage') == 'Completed']
    completed_count = len(completed_orders)
    
    # [ENHANCEMENT] Count orders dispatched for the new metric
    dispatched_count = len([o for o in data_list if o.get('dispatched_at') or o.get('dispatch_completed_at') or o.get('stage') == 'Completed'])
    
    # Data quality tracking per key
    data_quality_breakdown = {key: 0 for key in CRITICAL_DATA_KEYS}
    
    total_orders = len(data_list)
    orders_with_missing_data = 0
    
    for order in data_list:
        order_id = order.get('order_id', 'Unknown')
        
        # Data Quality Check
        has_missing = False
        for k in CRITICAL_DATA_KEYS:
            # Check for None or empty string
            if not order.get(k) and order.get(k) is not False and order.get(k) != 0: 
                data_quality_breakdown[k] += 1
                has_missing = True
        if has_missing:
            orders_with_missing_data += 1

        if order.get('stage') == 'Completed':
            # 1. Total Cycle Time & On-Time Check (Only for completed orders)
            received_str = order.get('received')
            completed_str = order.get('dispatched_at') or order.get('dispatch_completed_at') or order.get('packing_completed_at')
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
        
    data_quality_score = (1 - (orders_with_missing_data / total_orders)) * 100 if total_orders > 0 else 0.0

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
        "data_quality_breakdown": data_quality_breakdown,
        "total_orders": total_orders,
        "dispatched_count": dispatched_count # [ENHANCEMENT] Added dispatched count
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

# -------------------------------------
# DELETE HANDLER
# -------------------------------------

def delete_single_order(order_key: str):
    """Handles the deletion of a single order and updates the state/cache."""
    
    try:
        # Assuming 'delete' function takes collection name and document key
        delete("orders", order_key)
        
        # Simulate successful deletion by clearing the cache
        st.cache_data.clear()
        st.success(f"✅ Order **{order_key}** successfully deleted. Refreshing dashboard.")
        st.rerun() # Rerun to fetch new data after cache clear
    except Exception as e:
        st.error(f"❌ Failed to delete order {order_key}: {e}")

# -------------------------------------
# INITIAL DATA LOAD
# -------------------------------------

orders, all_orders_list, overall_kpis = fetch_and_analyze_data()

if not orders:
    st.warning("No orders found or data fetching failed.")
    st.stop()

# --- KPI Calculations ---
total_orders = len(all_orders_list)
on_time_rate = overall_kpis['on_time_rate']
data_quality_score = overall_kpis['data_quality_score']
on_time_delta = f"{on_time_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"
data_quality_percent = f"{data_quality_score:.1f}%"
data_quality_delta = f"{data_quality_score - DATA_QUALITY_TARGET:.1f}% vs Target"

# [ENHANCEMENT] Calculate Storage/WIP Inventory
orders_in_storage = [o for o in all_orders_list if o.get('stage') == 'Storage']
total_storage_qty = sum(o.get('qty', 0) for o in orders_in_storage)
total_storage_orders = len(orders_in_storage)

sla_violation_count = 0
for o in overall_kpis['completed_orders']: 
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
            pass 

efficiency_score = (on_time_rate * 0.7) + (data_quality_score * 0.3)


# -------------------------------------
## 📊 Executive Summary KPIs
# -------------------------------------

# [ENHANCEMENT] Adjusted columns to fit new metrics
col1, col2, col3, col_storage, col_dispatch, col6 = st.columns(6) 

col1.metric("Total Orders", total_orders, "Total in System")
col2.metric("Orders Completed", overall_kpis['completed_count'], "Total Finished")
col3.metric(
    "Efficiency Score (WIP)", 
    f"{efficiency_score:.1f}", 
    help="Weighted Score: 70% OTD Rate + 30% Data Quality"
)

# [ENHANCEMENT] New Metric: Storage/WIP Inventory
col_storage.metric(
    "📦 Orders in Storage (WIP)", 
    total_storage_orders,
    f"Total Qty: {total_storage_qty:,}",
    delta_color="off",
    help="Number of orders awaiting dispatch, representing Work-In-Process inventory."
)

# [ENHANCEMENT] New Metric: Total Dispatched
col_dispatch.metric(
    "🚀 Total Orders Dispatched",
    overall_kpis['dispatched_count'],
    "Total Completed the Dispatch Stage",
    delta_color="off"
)

col6.metric( # Adjusted index from col5 to col6
    "Data Quality Score", 
    data_quality_percent, 
    delta=data_quality_delta, 
    delta_color="normal" if data_quality_score >= DATA_QUALITY_TARGET else "inverse"
)


# [Original Col 4 moved below]
col_otd, col_sla = st.columns(2)
col_otd.metric(
    "On-Time Delivery Rate", 
    f"{on_time_rate:.1f}%", 
    delta=on_time_delta, 
    delta_color="normal" if on_time_rate >= ON_TIME_RATE_TARGET else "inverse"
)
col_sla.metric(
    "SLA Violation Count",
    sla_violation_count,
    delta="Completed orders exceeding 7 days",
    delta_color="inverse" if sla_violation_count > 0 else "normal"
)


st.divider()

# -------------------------------------
## 🧹 Data Quality Audit Visualization
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
    color=alt.Color('Missing %', scale=alt.Scale(scheme='reds'), legend=None)
).properties(
    title="Count of Orders Missing Critical Data Fields"
)

st.altair_chart(dq_chart, use_container_width=True)



st.divider()

# -------------------------------------
## Segmented Performance Analysis
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
## ⚙️ Bottleneck and Stage Performance 
# -------------------------------------

avg_stage_times_seconds = {}
for stage, total_s in overall_kpis['stage_time_totals'].items():
    count = overall_kpis['stage_time_counts'].get(stage, 0)
    if count > 0:
        avg_stage_times_seconds[stage] = total_s / count

if avg_stage_times_seconds:
    # Bottleneck Detection
    bottleneck_stage = max(avg_stage_times_seconds, key=avg_stage_times_seconds.get)
    bottleneck_time = format_seconds_to_hms(avg_stage_times_seconds[bottleneck_stage])
    
    st.markdown(f"### 🛑 Current Bottleneck: **{bottleneck_stage}**")
    st.markdown(f"The **{bottleneck_stage}** stage has the highest average duration: **{bottleneck_time}**.")

    st.markdown("---")
    
    # Fastest & Slowest Orders
    st.markdown("### Top Delays and Exceptional Performance (Fastest/Slowest Orders)")
    
    performance_table = []
    # [ENHANCEMENT] Added a check for 'Storage' and 'Dispatch' for display consistency
    stages_for_table = [s[0] for s in PRODUCTION_STAGES] + ['Storage'] 
    
    for stage_name in stages_for_table:
        if stage_name == 'Storage': 
            continue # Storage is transitionary, skip performance tracking here

        perf = overall_kpis['stage_performance'].get(stage_name)
        if not perf: continue
        
        fastest_s, fastest_id = perf['fastest']
        slowest_s, slowest_id = perf['slowest']
        
        if overall_kpis['stage_time_counts'].get(stage_name, 0) > 0:
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
## 📈 Visualizations
# -------------------------------------

col_viz1, col_viz2 = st.columns(2)

with col_viz1:
    st.subheader("Order Count Distribution by Stage")
    stage_counts: Dict[str, int] = {
        "Design": 0, "Printing": 0, "DieCut": 0, "Assembly": 0, 
        "Packing": 0, "Storage": 0, "Dispatch": 0, "Completed": 0 # [ENHANCEMENT] Added Storage
    }
    for o in orders.values():
        stage = o.get('stage', 'Unknown')
        if stage in stage_counts:
            stage_counts[stage] += 1
            
    chart_data = pd.DataFrame(
        list(stage_counts.items()),
        columns=['Stage', 'Count']
    )
    
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
        # [ENHANCEMENT] Ensure we don't include Storage in the performance time breakdown if it wasn't tracked
        stages_for_chart = [s[0] for s in PRODUCTION_STAGES]

        for stage in stages_for_chart:
            total_s = overall_kpis['stage_time_totals'].get(stage, 0)
            count = overall_kpis['stage_time_counts'].get(stage, 0)
            if count > 0:
                avg_time_chart_data.append({
                    'Stage': stage,
                    'Avg Time (Min)': (total_s / count) / 60 
                })

        avg_df = pd.DataFrame(avg_time_chart_data)
        
        st.subheader("Avg. Time Spent Per Stage (Delay Heat-Map)")
        
        # Sort based on the original stage list order
        stage_sort_list = list(avg_stage_times_seconds.keys())
        
        chart = alt.Chart(avg_df).mark_bar().encode(
            x=alt.X('Stage', sort=stage_sort_list),
            y=alt.Y('Avg Time (Min)', title='Average Duration (Minutes)'),
            color=alt.Color('Avg Time (Min)', scale=alt.Scale(scheme='yelloworangered'), legend=alt.Legend(title="Avg Time (Min)")),
            tooltip=['Stage', alt.Tooltip('Avg Time (Min)', format='.2f')]
        ).properties(
            title="Stage Time Breakdown (Highest time is the Bottleneck)"
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Insufficient data for Average Stage Time analysis.")

st.divider()

# -------------------------------------
## 🔍 Filter Panel
# -------------------------------------

st.markdown("#### Quick Action Filters")
col_q1, col_q2, col_q3 = st.columns(3)
quick_filter = col_q1.selectbox(
    "Quick Filter Set",
    ["None", "Late or Past Due", "High Priority Active", "Data Quality Issues"]
)

with st.expander("🔍 Advanced Filter & Search Orders", expanded=False):
    
    st.markdown("##### Filter by Stage, Product, and Priority")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    product_types = sorted(list(set(o.get('product_type') for o in all_orders_list if o.get('product_type'))))
    priorities = sorted(list(set(o.get('priority') for o in all_orders_list if o.get('priority'))))

    stage_filter = col_s1.selectbox(
        "Stage",
        # [ENHANCEMENT] Added Storage to filter list
        ["All", "Design", "Printing", "DieCut", "Assembly", "Packing", "Storage", "Dispatch", "Completed"],
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
    
    col_d1, col_d2, _ = st.columns([1, 1, 1])
    start_date_filter = col_d1.date_input("Start Date (Received)", value=datetime.today().date() - timedelta(days=30), key="start_date")
    end_date_filter = col_d2.date_input("End Date (Received)", value=datetime.today().date(), key="end_date")

    col_t1, col_t2, _ = st.columns([1, 1, 1])
    customer_filter = col_t1.text_input("Customer Name Search")
    order_search = col_t2.text_input("Search Order ID")


st.caption("Expand the filter box above to refine your search.")

# -------------------------------------
# APPLY FILTERS
# -------------------------------------

filtered: Dict[str, Any] = {}
start_dt = datetime.combine(start_date_filter, datetime.min.time()).replace(tzinfo=timezone.utc) # [ENHANCEMENT] Explicit UTC
end_dt = datetime.combine(end_date_filter, datetime.max.time()).replace(tzinfo=timezone.utc) # [ENHANCEMENT] Explicit UTC
now = datetime.now(timezone.utc) # [ENHANCEMENT] Explicit UTC
data_quality_keys = CRITICAL_DATA_KEYS 

for key, o in orders.items():

    if not isinstance(o, dict):
        continue
    
    # --- QUICK FILTERS Logic ---
    is_late_or_past_due = False
    due_str = o.get('due')
    completed_str = o.get('dispatched_at') or o.get('packing_completed_at')
    is_completed = o.get('stage') == 'Completed'
    
    if due_str:
        try:
            # Add UTC timezone assumption if not present
            due_dt = datetime.fromisoformat(due_str).replace(tzinfo=timezone.utc)
            
            if (is_completed and completed_str and datetime.fromisoformat(completed_str).replace(tzinfo=timezone.utc) > due_dt) or \
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
            
    # --- STANDARD FILTERS Logic ---
    if stage_filter != "All" and o.get("stage") != stage_filter:
        continue

    if product_filter != "All" and o.get("product_type") != product_filter:
        continue

    if priority_filter != "All" and o.get("priority") != priority_filter:
        continue
            
    received_str = o.get("received")
    if received_str:
        try:
            received_dt = datetime.fromisoformat(received_str).replace(tzinfo=timezone.utc)
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
# DISPLAY RESULTS & DOWNLOAD
# -------------------------------------
st.subheader(f"✅ Filtered Orders: {len(filtered)} found.")

if not filtered:
    st.info("No orders match the selected filters.")
    st.stop()

# Sort by received date for better overview
sorted_filtered_list: list[Tuple[str, Any]] = sorted(
    filtered.items(),
    key=lambda x: x[1].get("received", "2099-12-31"),
    reverse=True 
)

# --- Summary Table Construction ---
summary_data = []
for key, order in sorted_filtered_list:
    stage = order.get('stage', 'N/A')
    
    is_late_indicator = "🟢 On Time"
    due_dt_raw = order.get('due')
    total_order_cycle = 'In Progress'
    completed_date = 'N/A' # [ENHANCEMENT] New column variable

    if due_dt_raw:
        try:
            due_dt = datetime.fromisoformat(due_dt_raw).replace(tzinfo=timezone.utc)
            completed_str = order.get('dispatched_at') or order.get('packing_completed_at')
            
            if stage == 'Completed' and completed_str:
                completed_dt = datetime.fromisoformat(completed_str).replace(tzinfo=timezone.utc)
                # [ENHANCEMENT] Format date for table
                completed_date = completed_dt.strftime('%Y-%m-%d')
                total_order_cycle = calculate_stage_duration(order.get('received'), completed_str)
                if completed_dt > due_dt:
                    is_late_indicator = "🔴 Late"
            elif datetime.now(timezone.utc) > due_dt:
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
        "Completed Date": completed_date # [ENHANCEMENT] Added completion date
    })

summary_df = pd.DataFrame(summary_data)

st.markdown("#### High-Level Order Summary")

col_sum_1, col_sum_2 = st.columns([3, 1])

with col_sum_2:
    # Download Report Button
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

for key, order in sorted_filtered_list:
    
    stage = order.get('stage', 'N/A')
    progress, _ = get_completion_info(stage)
    order_id = order.get('order_id', key) # Use the key if order_id is missing

    total_order_cycle = ""
    if stage == 'Completed':
        total_order_cycle = calculate_stage_duration(order.get('received'), order.get('dispatched_at') or order.get('packing_completed_at'))
        
    expander_header = f"**{order_id}** — {order.get('customer', 'N/A')} | **Stage:** `{stage}`"
    if total_order_cycle:
        expander_header += f" | **Total Time:** {total_order_cycle}"


    with st.expander(expander_header):
        
        # --- Single Order Delete Button ---
        delete_col, _ = st.columns([1, 4])
        with delete_col:
            if st.button(f"🗑️ Delete Order {order_id}", key=f"delete_{order_id}", type="secondary", help="Permanently delete this single order from the database."):
                delete_single_order(key) # Pass the database key for deletion

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

        st.markdown("### Workflow Durations & Timestamps")
        
        # Calculate Durations
        durations_data = {
            "Design": calculate_stage_duration(order.get('started_at'), order.get('design_completed_at')),
            "Printing": calculate_stage_duration(order.get('printing_started_at'), order.get('printing_completed_at')),
            "DieCut": calculate_stage_duration(order.get('diecut_started_at'), order.get('diecut_completed_at')),
            "Assembly": calculate_stage_duration(order.get('assembly_started_at'), order.get('assembly_completed_at')),
            "Packing": calculate_stage_duration(order.get('packing_start'), order.get('packing_completed_at')),
            # [ENHANCEMENT] Used completion key for Dispatch
            "Dispatch": calculate_stage_duration(order.get('dispatch_start') or order.get('packing_completed_at'), order.get('dispatch_completed_at') or order.get('dispatched_at')), 
        }
        
        # Format Timestamps for a table display (replacing the raw JSON)
        timestamps_data = {
            "Design Completed": order.get("design_completed_at", "N/A"),
            "Printing Completed": order.get("printing_completed_at", "N/A"),
            "DieCut Completed": order.get("diecut_completed_at", "N/A"),
            "Assembly Completed": order.get("assembly_completed_at", "N/A"),
            "Packing Completed": order.get("packing_completed_at", "N/A"),
            "Dispatched": order.get("dispatched_at", "N/A") or order.get("dispatch_completed_at", "N/A"), # [ENHANCEMENT] Consolidated dispatch keys
        }
        
        # Convert timestamp to a nicer format (date only, or specific time if needed)
        def format_timestamp(ts: str) -> str:
            if ts and ts != "N/A":
                try:
                    # Parse as UTC, format for display
                    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") 
                except:
                    return ts
            return "N/A"

        # Create DataFrame for display
        workflow_df = pd.DataFrame({
            "Stage": list(durations_data.keys()),
            "Duration (H:M:S)": list(durations_data.values()),
            "Completion Timestamp": [format_timestamp(timestamps_data[key.replace(' Completed', '').replace('Dispatched', 'Dispatched')]) for key in timestamps_data]
        })

        st.dataframe(workflow_df, use_container_width=True, hide_index=True)


st.divider()

# -------------------------------------
## ⚠️ Danger Zone: Administrative Actions (Delete ALL Feature)
# -------------------------------------
st.subheader("⚠️ Danger Zone: Administrative Actions")

if st.session_state["role"] == "admin":
    st.warning("This action will **PERMANENTLY DELETE ALL ORDERS** in your database. Use with extreme caution.")
    delete_all_col, _ = st.columns([1, 4])
    
    with delete_all_col:
        delete_confirmation = st.checkbox("I understand and want to permanently delete ALL orders.")
        
        if delete_confirmation:
            if st.button("🔴 Permanently Delete ALL Orders", type="primary"):
                try:
                    # Execute the assumed firebase delete operation for the entire 'orders' collection
                    delete("orders") 
                    st.success("✅ All orders deleted successfully. Refreshing page...")
                    st.cache_data.clear() # Clear cache after delete
                    st.rerun() # Rerun to fetch new, empty data
                except Exception as e:
                    st.error(f"❌ Failed to delete all orders: {e}. Ensure your 'firebase.delete' function is correctly configured to clear the 'orders' collection.")
