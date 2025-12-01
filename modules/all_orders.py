import streamlit as st
import pandas as pd
import altair as alt
# Assuming 'firebase' module exists and has 'read', 'delete', and 'write' functions
from firebase import read, delete 
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional, List
from dateutil import parser 

# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="🚀 Executive Production Analytics (Actionable)", page_icon="📋", layout="wide")

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
    ('Dispatch', 'packing_completed_at', 'dispatched_at'),
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
    """Calculates key production metrics, including Cycle Time, On-Time Rate, Avg Stage Times, and Data Quality."""
    total_cycle_time_seconds = 0
    on_time_count = 0
    stage_time_totals = {stage[0]: 0.0 for stage in PRODUCTION_STAGES}
    stage_time_counts = {stage[0]: 0 for stage in PRODUCTION_STAGES}
    stage_performance = {stage[0]: {'fastest': (float('inf'), None), 'slowest': (0.0, None)} for stage in PRODUCTION_STAGES}
    completed_orders_analysis = []
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
                
                completed_orders_analysis.append({
                    'Order ID': order_id,
                    'Customer': order.get('customer', 'N/A'),
                    'Cycle Time (Hours)': cycle_time_seconds / 3600,
                    'On Time': "Yes" if is_on_time else "No",
                    'Firebase ID': order.get('firebase_id')
                })

            for stage, start_key, end_key in PRODUCTION_STAGES:
                s = get_stage_seconds(order, start_key, end_key)
                if s is not None:
                    stage_time_totals[stage] += s
                    stage_time_counts[stage] += 1
                    
                    if s < stage_performance[stage]['fastest'][0]:
                        stage_performance[stage]['fastest'] = (s, order_id)
                    if s > stage_performance[stage]['slowest'][0]:
                        stage_performance[stage]['slowest'] = (s, order_id)

    completed_count = len([o for o in data_list if o.get('stage') == 'Completed'])
    
    if completed_count > 0:
        avg_cycle_time_seconds = total_cycle_time_seconds / completed_count
        avg_cycle_time = format_seconds_to_hms(avg_cycle_time_seconds)
        on_time_rate = (on_time_count / completed_count) * 100
        
        avg_stage_times = {stage: format_seconds_to_hms(total_s / stage_time_counts[stage]) 
                           if stage_time_counts[stage] > 0 else "N/A" 
                           for stage, total_s in stage_time_totals.items()}
    else:
        avg_cycle_time = "N/A"
        on_time_rate = 0.0
        avg_stage_times = {}
        
    data_quality_score = (1 - (orders_with_missing_data / total_orders)) * 100 if total_orders > 0 else 0.0

    return {
        "completed_count": completed_count,
        "completed_orders_analysis": completed_orders_analysis,
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
        qty = int(order.get('qty', 0)) if str(order.get('qty', '0')).isdigit() else 0
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
    
    # FIX: Ensure 'orders' is a dict before attempting to iterate
    if not isinstance(orders, dict):
        return None, None, None, None # Return None for all data parts on failure
    
    orders_with_key = {}
    for key, o in orders.items():
        if isinstance(o, dict):
            o['firebase_id'] = key
            orders_with_key[key] = o
            
    if not orders_with_key:
        return None, None, None, None
    
    all_orders_list = list(orders_with_key.values())
    overall_kpis = analyze_kpis(all_orders_list)
    wip_inventory, total_wip_orders, wip_aging_list = analyze_wip(all_orders_list)
    return orders_with_key, all_orders_list, overall_kpis, (wip_inventory, total_wip_orders, wip_aging_list)

# -------------------------------------
# DELETE HANDLER
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

# --- START OF PART 2 ---
