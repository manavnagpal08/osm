import streamlit as st
import pandas as pd
import altair as alt
from firebase import read, delete 
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional, List
from dateutil import parser # Used for robust ISO parsing

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="🚀 Executive Production Analytics (Actionable)", page_icon="📋", layout="wide")

# -------------------------------------
# ROLE CHECK & PAGE SETUP
# -------------------------------------
if "role" not in st.session_state:
    # This assumes 'pages/login.py' is a valid path in your Streamlit app structure
    st.switch_page("pages/login.py")

if st.session_state["role"] != "admin":
    st.error("❌ Only admin can view this page.")
    st.stop()

st.title("🚀 Executive Production Analytics Dashboard (Actionable Intelligence)")
st.write("Focus on **Actionable Intelligence** — Identify bottlenecks, manage risk, and drive continuous improvement.")

# -------------------------------------
# CONFIGURATION
# -------------------------------------
# Target KPI for comparison
ON_TIME_RATE_TARGET = 85.0
DATA_QUALITY_TARGET = 95.0
SLA_CYCLE_TIME_HOURS = 168 # 7 days
ORDER_AGING_DAYS_WARNING = 7 # Orders in WIP for more than 7 days

# Define all possible production stages with their start/end keys
PRODUCTION_STAGES = [
    ('Design', 'started_at', 'design_completed_at'),
    ('Printing', 'printing_started_at', 'printing_completed_at'),
    ('DieCut', 'diecut_started_at', 'diecut_completed_at'),
    ('Assembly', 'assembly_started_at', 'assembly_completed_at'),
    ('Packing', 'packing_start', 'packing_completed_at'),
    ('Dispatch', 'packing_completed_at', 'dispatched_at'), # Added Dispatch for full cycle
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

def safe_iso_to_dt(iso_str: Optional[str]) -> Optional[datetime]:
    """Safely converts ISO string to timezone-aware datetime."""
    if iso_str:
        try:
            # Use dateutil.parser for robust parsing, ensuring UTC awareness
            dt = parser.isoparse(iso_str).astimezone(timezone.utc)
            return dt
        except Exception:
            return None
    return None

@st.cache_data(ttl=600)
def get_stage_seconds(order: Dict[str, Any], start_key: str, end_key: str) -> Optional[float]:
    """Safely calculates duration in seconds between two ISO timestamps."""
    start = order.get(start_key)
    end = order.get(end_key)
    t1 = safe_iso_to_dt(start)
    t2 = safe_iso_to_dt(end)
    if t1 and t2:
        return (t2 - t1).total_seconds()
    return None

def calculate_stage_duration(start_time: Optional[str], end_time: Optional[str]) -> str:
    """Calculates the duration between two ISO format timestamps and returns H:M:S."""
    diff_seconds = get_stage_seconds({'start': start_time, 'end': end_time}, 'start', 'end')
    if diff_seconds is not None:
        return f"**{format_seconds_to_hms(diff_seconds)}**"
    
    if start_time and not end_time:
        # Calculate time in progress if the stage started but hasn't finished
        start_dt = safe_iso_to_dt(start_time)
        if start_dt:
            in_progress_seconds = (datetime.now(timezone.utc) - start_dt).total_seconds()
            return f"In Progress ({format_seconds_to_hms(in_progress_seconds)})"
            
    return "In Progress"

def get_completion_info(stage: str) -> Tuple[float, str]:
    """Returns progress percentage and status color based on stage."""
    stages = ["Design", "Printing", "DieCut", "Assembly", "Packing", "Dispatch", "Completed"]
    if stage == 'Completed':
        return 1.0, "green"
    try:
        # Use +1 for the current stage, +0.5 is fine for display
        index = stages.index(stage)
        progress = (index + 0.5) / len(stages) 
        color = "blue"
        if stage in ["Packing", "Dispatch"]:
            color = "orange"
        return progress, color
    except ValueError:
        return 0.05, "gray"

@st.cache_data(ttl=600)
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

    completed_orders_analysis = [] # To store details for the new performance ranking
    
    data_quality_breakdown = {key: 0 for key in CRITICAL_DATA_KEYS}
    total_orders = len(data_list)
    orders_with_missing_data = 0
    
    for order in data_list:
        order_id = order.get('order_id', 'Unknown')
        
        # Data Quality Check
        has_missing = False
        if order.get('received'):
            for k in CRITICAL_DATA_KEYS:
                if not order.get(k):
                    data_quality_breakdown[k] += 1
                    has_missing = True
            if has_missing:
                orders_with_missing_data += 1

        if order.get('stage') == 'Completed':
            received_dt = safe_iso_to_dt(order.get('received'))
            completed_dt = safe_iso_to_dt(order.get('dispatched_at') or order.get('packing_completed_at'))
            due_dt = safe_iso_to_dt(order.get('due'))

            if received_dt and completed_dt:
                cycle_time_seconds = (completed_dt - received_dt).total_seconds()
                total_cycle_time_seconds += cycle_time_seconds
                
                is_on_time = False
                if due_dt and completed_dt <= due_dt:
                    on_time_count += 1
                    is_on_time = True
                
                # Store data for Performance Ranking
                completed_orders_analysis.append({
                    'Order ID': order_id,
                    'Customer': order.get('customer', 'N/A'),
                    'Cycle Time (Hours)': cycle_time_seconds / 3600,
                    'On Time': "Yes" if is_on_time else "No",
                    'Firebase ID': order.get('firebase_id') # Useful for linking back if needed
                })

            # Individual Stage Times & Performance Tracking
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

    completed_count = len([o for o in data_list if o.get('stage') == 'Completed'])
    
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
        "completed_orders_analysis": completed_orders_analysis, # New ranking data
        "on_time_count": on_time_count,
        "avg_cycle_time": avg_cycle_time,
        "on_time_rate": on_time_rate,
        "avg_stage_times": avg_stage_times,
        "stage_time_totals": stage_time_totals,
        "stage_time_counts": stage_time_counts,
        "stage_performance": stage_performance,
        "data_quality_score": data_quality_score,
        "data_quality_breakdown": data_quality_breakdown,
        "total_orders": total_orders
    }

@st.cache_data(ttl=600)
def analyze_wip(data_list: List[Dict[str, Any]]):
    """Calculates WIP metrics, including aging."""
    wip_inventory = {}
    wip_aging_list = []
    
    now = datetime.now(timezone.utc)
    
    wip_orders = [
        o for o in data_list 
        if o.get('stage') not in ['Completed', 'Dispatch'] and o.get('received') is not None
    ]

    for order in wip_orders:
        product_type = order.get('product_type', 'Unknown')
        try:
            qty = int(order.get('qty', 0))
        except (ValueError, TypeError):
            qty = 0 
        
        received_dt = safe_iso_to_dt(order.get('received'))
        aging_days = (now - received_dt).total_seconds() / (24 * 3600) if received_dt else 0
        
        wip_aging_list.append({
            'Order ID': order.get('order_id', 'N/A'),
            'Customer': order.get('customer', 'N/A'),
            'Stage': order.get('stage', 'N/A'),
            'Aging (Days)': aging_days,
        })
        
        if product_type not in wip_inventory:
            wip_inventory[product_type] = {'total_qty': 0, 'order_count': 0, 'max_aging_days': 0}
        
        wip_inventory[product_type]['total_qty'] += qty
        wip_inventory[product_type]['order_count'] += 1
        wip_inventory[product_type]['max_aging_days'] = max(wip_inventory[product_type]['max_aging_days'], aging_days)
        
    return wip_inventory, len(wip_orders), wip_aging_list

# -------------------------------------
# FETCH & PRE-ANALYZE ORDERS
# -------------------------------------
@st.cache_data(ttl=600)
def fetch_and_analyze_data():
    """Fetches data and runs the initial, cached KPI analysis."""
    orders: Dict[str, Any] = read("orders") or {}
    
    # Add firebase key to orders for easy lookup
    orders_with_key = {}
    for key, o in orders.items():
        if isinstance(o, dict):
            o['firebase_id'] = key
            orders_with_key[key] = o
            
    if not orders_with_key:
        return None, None, 0, None
    
    all_orders_list = list(orders_with_key.values())
    overall_kpis = analyze_kpis(all_orders_list)
    wip_inventory, total_wip_orders, wip_aging_list = analyze_wip(all_orders_list)
    return orders_with_key, all_orders_list, overall_kpis, (wip_inventory, total_wip_orders, wip_aging_list)

# -------------------------------------
# DELETE HANDLER (UNCHANGED)
# -------------------------------------

def delete_single_order(order_key: str):
    """Handles the deletion of a single order and updates the state/cache."""
    
    try:
        delete("orders", order_key)
        st.cache_data.clear()
        st.success(f"✅ Order **{order_key}** successfully deleted. Refreshing dashboard.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to delete order {order_key}: {e}")

# -------------------------------------
# INITIAL DATA LOAD
# -------------------------------------

orders, all_orders_list, overall_kpis, wip_data = fetch_and_analyze_data()

if not orders:
    st.warning("No orders found or data fetching failed.")
    st.stop()

wip_inventory, total_wip_orders, wip_aging_list = wip_data

# --- KPI Calculations ---
total_orders = len(all_orders_list)
on_time_rate = overall_kpis['on_time_rate']
data_quality_score = overall_kpis['data_quality_score']
on_time_delta = f"{on_time_rate - ON_TIME_RATE_TARGET:.1f}% vs Target"
data_quality_percent = f"{data_quality_score:.1f}%"
data_quality_delta = f"{data_quality_score - DATA_QUALITY_TARGET:.1f}% vs Target"

sla_violation_count = 0
for o in overall_kpis['completed_orders_analysis']: 
    if o['Cycle Time (Hours)'] > SLA_CYCLE_TIME_HOURS:
        sla_violation_count += 1

efficiency_score = (on_time_rate * 0.7) + (data_quality_score * 0.3)


# -------------------------------------
## 📊 Executive Summary KPIs
# -------------------------------------

# Adjusted to 7 columns (Metrics + Gauges)
col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

col1.metric("Total Orders", total_orders, "Total in System")
col2.metric("Orders Completed", overall_kpis['completed_count'], "Total Finished")
col3.metric(
    "Total WIP Orders", 
    total_wip_orders, 
    "Active Production (Non-Completed)"
)
col4.metric(
    "Efficiency Score", 
    f"{efficiency_score:.1f}", 
    help="Weighted Score: 70% OTD Rate + 30% Data Quality"
)

# New: KPI Gauges for instant comparison
# Gauge for OTD Rate
otd_gauge = alt.Chart(pd.DataFrame({'value': [on_time_rate], 'target': [ON_TIME_RATE_TARGET]})).mark_arc(innerRadius=20).encode(
    theta=alt.Theta("value", stack=True),
    color=alt.condition(
        alt.datum.value >= alt.datum.target,
        alt.value("green"),
        alt.value("red")
    ),
    tooltip=['value']
).properties(title=f"OTD Rate ({on_time_rate:.1f}%)")

col5.metric(
    "On-Time Delivery Rate", 
    f"{on_time_rate:.1f}%", 
    delta=on_time_delta, 
    delta_color="normal" if on_time_rate >= ON_TIME_RATE_TARGET else "inverse"
)
# col5.altair_chart(otd_gauge, use_container_width=True)


col6.metric(
    "SLA Violation Count",
    sla_violation_count,
    delta=f"Completed orders > {SLA_CYCLE_TIME_HOURS} hrs",
    delta_color="inverse" if sla_violation_count > 0 else "normal"
)

# Gauge for Data Quality Score
dq_gauge = alt.Chart(pd.DataFrame({'value': [data_quality_score], 'target': [DATA_QUALITY_TARGET]})).mark_arc(innerRadius=20).encode(
    theta=alt.Theta("value", stack=True),
    color=alt.condition(
        alt.datum.value >= alt.datum.target,
        alt.value("blue"),
        alt.value("orange")
    ),
    tooltip=['value']
).properties(title=f"DQ Score ({data_quality_score:.1f}%)")

col7.metric(
    "Data Quality Score", 
    data_quality_percent, 
    delta=data_quality_delta, 
    delta_color="normal" if data_quality_score >= DATA_QUALITY_TARGET else "inverse"
)
# col7.altair_chart(dq_gauge, use_container_width=True)

st.divider()

# -------------------------------------
## 🏭 Work In Progress (WIP) & Aging Risk
# -------------------------------------

st.subheader("🏭 Work In Progress (WIP) & Aging Risk Analysis")
st.write(f"Showing inventory for **{total_wip_orders}** active orders currently in production.")

if total_wip_orders > 0:
    col_wip1, col_wip2 = st.columns([1, 2])
    
    with col_wip1:
        wip_df = pd.DataFrame([
            {'Product Type': k, 'Total Quantity (Units)': v['total_qty'], 'Active Orders': v['order_count'], 'Max Aging (Days)': v['max_aging_days']}
            for k, v in wip_inventory.items()
        ])
        
        total_wip_qty = wip_df['Total Quantity (Units)'].sum()
        st.metric("Total Active WIP Quantity", f"{total_wip_qty:,} units", "Aggregate units currently in flow")
        
        # Highlight aging risk in the summary
        aging_risk_count = len([a for a in wip_aging_list if a['Aging (Days)'] > ORDER_AGING_DAYS_WARNING])
        aging_risk_delta = f"Orders > {ORDER_AGING_DAYS_WARNING} days"
        st.metric(
            "WIP Aging Risk",
            aging_risk_count,
            delta=aging_risk_delta,
            delta_color="inverse" if aging_risk_count > 0 else "normal",
            help="Number of active WIP orders that have been in the system longer than the warning threshold."
        )

        st.dataframe(wip_df, use_container_width=True, hide_index=True)
        
    with col_wip2:
        st.markdown("##### WIP Aging Breakdown (Stale Inventory Identification)")
        
        wip_aging_df = pd.DataFrame(wip_aging_list)
        
        # Custom coloring for aging
        def highlight_aging(s):
            is_stale = s['Aging (Days)'] > ORDER_AGING_DAYS_WARNING
            return ['background-color: #ffcccc' if v else '' for v in is_stale]
        
        st.dataframe(
            wip_aging_df.sort_values(by='Aging (Days)', ascending=False).style.apply(highlight_aging, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Aging (Days)": st.column_config.NumberColumn("Aging (Days)", format="%.1f days", help="Time since order was received.")
            }
        )
        st.caption(f"Rows highlighted in red are orders older than **{ORDER_AGING_DAYS_WARNING} days**.")

else:
    st.info("No orders currently in active Work In Progress (WIP).")

st.divider()


# -------------------------------------
## ⚙️ Actionable Bottleneck and Stage Performance 
# -------------------------------------

avg_stage_times_seconds = {}
for stage, total_s in overall_kpis['stage_time_totals'].items():
    count = overall_kpis['stage_time_counts'].get(stage, 0)
    if count > 0:
        avg_stage_times_seconds[stage] = total_s / count

st.subheader("🛑 Bottleneck Identification & Action")

if avg_stage_times_seconds:
    # Bottleneck Detection
    bottleneck_stage = max(avg_stage_times_seconds, key=avg_stage_times_seconds.get)
    bottleneck_time = format_seconds_to_hms(avg_stage_times_seconds[bottleneck_stage])
    
    st.error(f"### 🚨 Current Bottleneck: **{bottleneck_stage}** ({bottleneck_time})")
    st.markdown("The **longest average completion time** suggests the primary constraint on throughput.")

    col_btnk1, col_btnk2 = st.columns(2)
    
    # Actionable Intelligence: Display the orders that caused the slowest time
    slowest_s, slowest_id = overall_kpis['stage_performance'][bottleneck_stage]['slowest']
    slowest_time_hms = format_seconds_to_hms(slowest_s)
    
    with col_btnk1:
        st.info(f"The single **longest delay** that drove this average was in order **`{slowest_id or 'N/A'}`** with a time of **{slowest_time_hms}**.")
    
    with col_btnk2:
        # NEW: Filter orders to quickly investigate the bottleneck stage
        if st.button(f"🔍 Filter to Orders in **{bottleneck_stage}** Stage", type="primary"):
            st.session_state['stage_f'] = bottleneck_stage
            st.toast(f"Applying filter: Stage = {bottleneck_stage}")
            # Ensure quick filter is cleared if set
            st.session_state['quick_filter'] = "None" 
            st.rerun()

    st.markdown("---")
    
    # Fastest & Slowest Orders Table (UNCHANGED but moved for flow)
    st.markdown("##### Top Delays and Exceptional Performance (Fastest/Slowest Orders)")
    
    performance_table = []
    for stage in PRODUCTION_STAGES:
        stage_name = stage[0]
        perf = overall_kpis['stage_performance'][stage_name]
        
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
## 🏆 Completed Orders Performance Ranking (New!)
# -------------------------------------

st.subheader("🏆 Completed Order Performance Ranking")
st.write("Analyze completed orders to identify best practices (fastest cycle time) and root causes for delays.")

if overall_kpis['completed_orders_analysis']:
    rank_df = pd.DataFrame(overall_kpis['completed_orders_analysis'])
    
    # Sort by Cycle Time for ranking
    rank_df['Rank'] = rank_df['Cycle Time (Hours)'].rank(method='min', ascending=True).astype(int)
    
    # Convert cycle time back to H:M:S for display
    rank_df['Cycle Time (H:M:S)'] = rank_df['Cycle Time (Hours)'].apply(lambda h: format_seconds_to_hms(h * 3600))
    
    # Final display columns
    display_cols = ['Rank', 'Order ID', 'Customer', 'Cycle Time (H:M:S)', 'On Time', 'Cycle Time (Hours)']

    # Filter for top 10 fastest and bottom 10 slowest
    col_rank_1, col_rank_2 = st.columns(2)
    
    with col_rank_1:
        st.markdown("##### 🥇 Top 10 Fastest Orders (Best Performers)")
        st.dataframe(
            rank_df.sort_values(by='Rank', ascending=True).head(10)[display_cols[:-1]], # Exclude raw hours column
            use_container_width=True,
            hide_index=True
        )

    with col_rank_2:
        st.markdown("##### 🐌 Top 10 Slowest Orders (Highest Delays)")
        st.dataframe(
            rank_df.sort_values(by='Rank', ascending=False).head(10)[display_cols[:-1]], # Exclude raw hours column
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No completed orders to generate performance rankings.")

st.divider()

# -------------------------------------
## 🧹 Data Quality Audit Visualization
# -------------------------------------

st.subheader("🧹 Data Quality Audit: Missing Critical Data")
st.write(f"Ensure all **{len(CRITICAL_DATA_KEYS)}** critical fields are populated. Overall Score: **{data_quality_percent}**")

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
    color=alt.Color('Missing %', scale=alt.Scale(scheme='reds', domain=[0, max(dq_df['Missing %'].max(), 10)]), legend=None) # Set domain to avoid colorless charts
).properties(
    title="Count of Orders Missing Critical Data Fields"
)
st.altair_chart(dq_chart, use_container_width=True)


st.divider()

# -------------------------------------
## 🔍 Filter Panel
# -------------------------------------
# Ensure filter state is initialized for quick button re-runs
if 'stage_f' not in st.session_state: st.session_state['stage_f'] = "All"
if 'product_f' not in st.session_state: st.session_state['product_f'] = "All"
if 'priority_f' not in st.session_state: st.session_state['priority_f'] = "All"
if 'quick_filter' not in st.session_state: st.session_state['quick_filter'] = "None"
if 'start_date' not in st.session_state: st.session_state['start_date'] = datetime.today().date() - timedelta(days=30)
if 'end_date' not in st.session_state: st.session_state['end_date'] = datetime.today().date()

st.markdown("#### Quick Action Filters")
col_q1, col_q2, col_q3 = st.columns(3)
quick_filter = col_q1.selectbox(
    "Quick Filter Set",
    ["None", "Late or Past Due", "High Priority Active", "Data Quality Issues"],
    key='quick_filter' # Persist quick filter selection
)

# ... (Rest of the Filter Panel code remains the same) ...
with st.expander("🔍 Advanced Filter & Search Orders", expanded=False):
    
    st.markdown("##### Filter by Stage, Product, and Priority")
    col_s1, col_s2, col_s3 = st.columns(3)
    
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
    
    col_d1, col_d2, _ = st.columns([1, 1, 1])
    start_date_filter = col_d1.date_input("Start Date (Received)", value=st.session_state.start_date, key="start_date")
    end_date_filter = col_d2.date_input("End Date (Received)", value=st.session_state.end_date, key="end_date")

    col_t1, col_t2, _ = st.columns([1, 1, 1])
    customer_filter = col_t1.text_input("Customer Name Search")
    order_search = col_t2.text_input("Search Order ID")


st.caption("Expand the filter box above to refine your search.")

# -------------------------------------
# APPLY FILTERS (UNCHANGED)
# -------------------------------------

filtered: Dict[str, Any] = {}
start_dt = datetime.combine(start_date_filter, datetime.min.time(), timezone.utc) # Ensure timezone awareness
end_dt = datetime.combine(end_date_filter, datetime.max.time(), timezone.utc)
now = datetime.now(timezone.utc)
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
        due_dt = safe_iso_to_dt(due_str)
        if due_dt:
            if (is_completed and completed_str and safe_iso_to_dt(completed_str) > due_dt) or \
               (not is_completed and now > due_dt):
                is_late_or_past_due = True
    
    if quick_filter == "Late or Past Due" and not is_late_or_past_due:
        continue
        
    elif quick_filter == "High Priority Active" and (o.get('priority') != 'High' or is_completed):
        continue

    elif quick_filter == "Data Quality Issues" and not any(not o.get(k) and o.get('received') for k in data_quality_keys):
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
        received_dt = safe_iso_to_dt(received_str)
        if received_dt and (received_dt < start_dt or received_dt > end_dt):
            continue
    
    if customer_filter and customer_filter.lower() not in o.get("customer", "").lower():
        continue

    if order_search and order_search.lower() not in o.get("order_id", "").lower():
        continue

    filtered[key] = o

# -------------------------------------
# DISPLAY RESULTS & DOWNLOAD (UNCHANGED)
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

    if due_dt_raw:
        due_dt = safe_iso_to_dt(due_dt_raw)
        completed_str = order.get('dispatched_at') or order.get('packing_completed_at')
        
        if due_dt:
            if stage == 'Completed' and completed_str:
                total_order_cycle = calculate_stage_duration(order.get('received'), completed_str)
                completed_dt = safe_iso_to_dt(completed_str)
                if completed_dt and completed_dt > due_dt:
                    is_late_indicator = "🔴 Late"
            elif stage != 'Completed' and datetime.now(timezone.utc) > due_dt:
                is_late_indicator = "🟠 Past Due"
        else:
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
    order_id = order.get('order_id', key)

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
        
        # Calculate Durations and Timestamps for a unified table
        
        workflow_data = []
        
        # Stages with start/end keys
        for stage_name, start_key, end_key in PRODUCTION_STAGES:
             duration_hms = calculate_stage_duration(order.get(start_key), order.get(end_key))
             completion_ts = format_timestamp(order.get(end_key, "N/A"))
             
             # Only show 'Dispatch' if it has started/completed
             if stage_name == 'Dispatch' and completion_ts == 'N/A':
                 continue
                 
             workflow_data.append({
                 "Stage": stage_name,
                 "Duration (H:M:S)": duration_hms,
                 "Completed Timestamp": completion_ts,
             })

        # Final table display
        if workflow_data:
            st.dataframe(pd.DataFrame(workflow_data), use_container_width=True, hide_index=True)
        else:
             st.info("No stage completion timestamps recorded for this order.")
