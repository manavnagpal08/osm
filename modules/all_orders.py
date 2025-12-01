import streamlit as st
import pandas as pd
import plotly.express as px
from firebase import read, update, delete 
from datetime import datetime, timezone, date, timedelta
import time
import numpy as np 

# --- CONFIGURATION ---
DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
FIREBASE_TIMEZONE = timezone.utc 

# ------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------------

def get_current_firebase_time_str():
    """Returns the current UTC time in ISO format for Firebase storage."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def to_datetime_utc(x):
    """Converts ISO format string to UTC timezone aware datetime object."""
    if not x:
        return None
    try:
        dt = datetime.fromisoformat(str(x).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

# ------------------------------------------------------------------------------------
# STICKY FILTER LOGIC (Query Params)
# ------------------------------------------------------------------------------------

def get_sticky_filter_state(key, default_value):
    """Reads filter state from URL or returns default."""
    try:
        param = st.query_params.get(key)
        if param:
            return param 
        return default_value
    except Exception:
        return default_value 

def set_sticky_filter_state(key, value):
    """Saves filter state to URL."""
    try:
        if st.query_params.get(key) != str(value):
            st.query_params[key] = str(value)
    except Exception as e:
        pass

# ------------------------------------------------------------------------------------
# ADMIN ACCESS & PAGE SETUP
# ------------------------------------------------------------------------------------

st.set_page_config(page_title="🔥 Advanced Orders Admin Panel (UX Optimized)", layout="wide") 

if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Access Denied — Admin Only")
    st.stop()

# ------------------------------------------------------------------------------------
# LOAD & PRE-PROCESS ORDERS (Fixes for all data type issues)
# ------------------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_and_process_orders():
    """Loads orders from Firebase and performs initial data cleaning and advanced metrics."""
    orders = read("orders") or {}
    data = []
    for key, o in orders.items():
        if isinstance(o, dict):
            o["firebase_id"] = key
            if 'qty' not in o or o['qty'] is None:
                o['qty'] = 0 
            data.append(o)

    df = pd.DataFrame(data)

    if df.empty:
        return pd.DataFrame(), {}, []

    production_stages = [
        "Received", "Design", "Printing", "Lamination",
        "DieCut", "Assembly", "Storage", "Dispatch", "Completed"
    ]

    stage_times = {
        "Received": "received", 
        "Design": "design_completed_at",
        "Printing": "printing_completed_at",
        "Lamination": "lamination_completed_at",
        "DieCut": "diecut_completed_at",
        "Assembly": "assembly_completed_at",
        "Storage": "storage_completed_at",
        "Dispatch": "dispatch_completed_at",
        "Completed": "dispatch_completed_at", 
    }

    # Data Quality: Robust conversion for ALL time fields.
    all_time_keys = list(set(stage_times.values()) | set(['due']))
    
    for key in all_time_keys:
        if key in df.columns:
            # Force conversion to datetime64[ns, UTC]. This is the safest way.
            df[key] = pd.to_datetime(df[key].apply(to_datetime_utc), utc=True, errors='coerce')

    # Prepare columns for the data_editor 
    df["Qty"] = df.get('qty', pd.Series()).fillna(0).astype(int)
    
    # Convert Timestamp to a Python date object for st.data_editor compatibility
    df["Due_Date"] = df['due'].dt.date.replace({pd.NaT: None})
    
    # --- Advanced Metric: Time to Deadline ---
    # Calculate time remaining/overdue in days
    current_time = datetime.now(timezone.utc)
    # The 'due' column is already guaranteed to be datetime64[ns, UTC]
    time_delta = df['due'] - current_time
    df['Time_To_Deadline'] = (time_delta.dt.total_seconds() / (24 * 3600)).round(1) # Days

    # Calculate Time-In-Stage
    for i in range(1, len(production_stages)):
        prev_stage = production_stages[i-1]
        
        start_col = stage_times.get(prev_stage)
        end_col = stage_times.get(production_stages[i])

        if start_col in df.columns and end_col in df.columns:
            duration_timedelta = (df[end_col] - df[start_col])
            duration_seconds = duration_timedelta.dt.total_seconds().fillna(0)
            df[f"{prev_stage}_duration_hours"] = (duration_seconds / 3600).round(2)


    return df, stage_times, production_stages


df, stage_times, production_stages = load_and_process_orders()

# ------------------------------------------------------------------------------------
# PAGE LAYOUT START
# ------------------------------------------------------------------------------------

st.title("🛡️ Admin — Orders Management & Advanced Analytics")
st.markdown("---")

if df.empty:
    st.warning("No orders found in the system.")
    st.stop()
    
## 🎯 Key Performance Indicators
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Orders", len(df))
col2.metric("Completed Orders", len(df[df["stage"] == "Completed"]))
col3.metric("Active Orders", len(df[df["stage"] != "Completed"]), 
            delta=f"{len(df[df['stage'] != 'Completed'])/len(df)*100:.1f}% of Total" if len(df) > 0 else "0%")
# REINTRODUCED DATE METRIC
orders_this_month = len(df[df["received"].dt.strftime("%Y-%m") == datetime.now().strftime("%Y-%m")])
col4.metric("Orders This Month", orders_this_month) 
col5.metric("Avg Order Qty", f"{df['Qty'].mean():.0f}" if 'Qty' in df else "N/A")

st.markdown("---")

## 🔍 Order Filtering (Sticky Filters)
with st.expander("Filter Options"):
    c1, c2 = st.columns(2)

    default_stage = get_sticky_filter_state("stage", "All")
    default_priority = get_sticky_filter_state("priority", "All")
    
    stage_filter = c1.selectbox(
        "Filter by Production Stage",
        ["All"] + production_stages,
        index=(["All"] + production_stages).index(default_stage) if default_stage in (["All"] + production_stages) else 0,
        key="stage_filter_select",
        on_change=lambda: set_sticky_filter_state("stage", st.session_state.stage_filter_select)
    )
    priority_filter = c2.selectbox(
        "Filter by Priority",
        ["All", "High", "Medium", "Low"],
        index=(["All", "High", "Medium", "Low"]).index(default_priority) if default_priority in (["All", "High", "Medium", "Low"]) else 0,
        key="priority_filter_select",
        on_change=lambda: set_sticky_filter_state("priority", st.session_state.priority_filter_select)
    )

df_filtered = df.copy()

if stage_filter != "All":
    df_filtered = df_filtered[df_filtered["stage"] == stage_filter]

if priority_filter != "All":
    df_filtered = df_filtered[df_filtered["priority"] == priority_filter]

# Add a warning if filtered DataFrame is empty
if df_filtered.empty:
    st.warning("No orders match the current filter criteria.")

# ------------------------------------------------------------------------------------
## 📋 Orders Table (Inline Edit, Sort, Search, Paginate)
# ------------------------------------------------------------------------------------
st.markdown("## 📋 Orders Table (Inline Edit, Sort, Search, Paginate)")

# Select columns for display and editing
df_display = df_filtered[[
    "order_id", "customer", "customer_phone", "item", "Qty", 
    "stage", "priority", "Due_Date", "Time_To_Deadline", "firebase_id" 
]].rename(columns={
    "customer_phone": "Phone",
    "order_id": "Order ID",
    "customer": "Customer",
    "item": "Item",
    "stage": "Stage",
    "priority": "Priority",
    "firebase_id": "Firebase ID",
    "Time_To_Deadline": "Deadline (Days)" # Rename advanced column
})

# Define the data editor configuration for inline editing
column_config = {
    "Order ID": st.column_config.TextColumn("Order ID", disabled=True),
    "Customer": st.column_config.TextColumn("Customer Name", required=True),
    "Phone": st.column_config.TextColumn("Customer Phone"),
    "Item": st.column_config.TextColumn("Item / Product", disabled=True),
    "Qty": st.column_config.NumberColumn("Qty", required=True, min_value=0),
    "Stage": st.column_config.TextColumn("Stage", disabled=True),
    "Priority": st.column_config.SelectboxColumn("Priority", options=["High", "Medium", "Low"], required=True),
    "Due_Date": st.column_config.DateColumn("Due Date", format="YYYY-MM-DD", required=True), 
    "Deadline (Days)": st.column_config.NumberColumn(
        "Deadline (Days)",
        help="Days remaining until the deadline (negative means overdue)",
        format="%.1f days",
        disabled=True
    ),
    "Firebase ID": st.column_config.Column("Firebase ID", disabled=True) 
}

edited_df = st.data_editor(
    df_display,
    column_config=column_config,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed", 
    key="orders_data_editor"
)

# Check for changes and update Firebase
if st.session_state.orders_data_editor['edited_rows']:
    st.info("🚨 Changes detected in the table. Applying updates to Firebase...")
    
    edited_rows = st.session_state.orders_data_editor['edited_rows']
    
    for position, edits in edited_rows.items():
        # ⭐ CRITICAL FIX: Get the original index value from the filtered DataFrame
        # using the positional indexer (`position`), then use that index value 
        # to access the row data in df_filtered by `.loc[index_value]`.
        original_index_value = df_filtered.iloc[position].name 
        original_firebase_id = df_filtered.loc[original_index_value, 'firebase_id']
        order_id_for_toast = df_filtered.loc[original_index_value, 'order_id']

        update_data = {}
        
        if 'Customer' in edits:
            update_data['customer'] = edits['Customer']
        if 'Phone' in edits:
            update_data['customer_phone'] = edits['Phone']
        if 'Qty' in edits:
            update_data['qty'] = int(edits['Qty'])
        if 'Priority' in edits:
            update_data['priority'] = edits['Priority']
        if 'Due_Date' in edits:
            try:
                date_obj = edits['Due_Date']
                # Convert the date object to a datetime object at the end of the day, set to UTC
                dt_obj = datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59, tzinfo=timezone.utc)
                update_data['due'] = dt_obj.isoformat().replace('+00:00', 'Z')
            except ValueError:
                st.error(f"Invalid date format for order {order_id_for_toast}. Date not updated.")
                continue

        if update_data:
            update(f"orders/{original_firebase_id}", update_data)
            st.toast(f"✅ Updated Order ID: {order_id_for_toast}", icon='💾')

    time.sleep(0.5) 
    st.session_state.orders_data_editor['edited_rows'] = {}
    st.cache_data.clear()
    st.rerun()

st.markdown("---")

## ⚡ Actions
colA, colB = st.columns(2)

csv_export = df_filtered.to_csv(index=False).encode()
colA.download_button(
    "📥 Export Filtered Data to CSV", csv_export, "orders_filtered_export.csv", "text/csv"
)

if colB.button("🗑️ Delete ALL Orders", type="secondary"):
    if st.session_state.get("confirm_delete_all") != True:
        st.session_state["confirm_delete_all"] = True
        st.warning("⚠️ Are you sure? Click again to confirm **DELETION OF ALL** orders.")
    else:
        with st.spinner("Deleting all orders..."):
            for key in df["firebase_id"]:
                delete(f"orders/{key}")
            st.success("All orders deleted.")
            st.session_state.pop("confirm_delete_all", None)
            st.cache_data.clear() 
            st.rerun()

st.markdown("---")

## 📈 Advanced Analytics Dashboard

col_an1, col_an2 = st.columns(2)

# Order Status Distribution (Pie Chart)
with col_an1:
    st.markdown("### 🟢 Order Status Distribution")
    fig_stage = px.pie(
        df,
        names="stage",
        title="Current Production Stage Breakdown",
        hole=.3
    )
    st.plotly_chart(fig_stage, use_container_width=True)

# Monthly production (Reintroduced)
with col_an2:
    st.markdown("### 🗓️ Monthly Orders Volume")
    df["received_month"] = df["received"].dt.to_period("M").astype(str)
    
    fig_m = px.bar(
        df.groupby("received_month").size().reset_index(name="count"),
        x="received_month",
        y="count",
        title="Orders Received by Month",
        labels={"received_month": "Month", "count": "Order Count"},
        color="count",
        color_continuous_scale=px.colors.sequential.Agsunset,
    )
    st.plotly_chart(fig_m, use_container_width=True)

### ⏱️ Bottleneck Analysis: Average Time to Complete Stage (Hours)
st.markdown("### ⏱️ Bottleneck Analysis: Average Time to Complete Stage (Hours)")


stage_duration_cols = [c for c in df.columns if c.endswith('_duration_hours')]

if stage_duration_cols:
    
    dept_times_avg = df[stage_duration_cols].mean().reset_index()
    dept_times_avg.columns = ["Duration_Column", "AvgHours"]
    
    dept_times_avg["Department"] = dept_times_avg["Duration_Column"].str.replace('_duration_hours', '')

    df_d = dept_times_avg[dept_times_avg["AvgHours"] > 0.01].dropna() 

    if not df_d.empty:
        fig_d = px.bar(
            df_d.sort_values("AvgHours", ascending=False), 
            x="Department",
            y="AvgHours",
            title="Average Stage Completion Time (Hours)",
            color="AvgHours", 
            color_continuous_scale=px.colors.sequential.Sunset,
        )
        st.plotly_chart(fig_d, use_container_width=True)

        slowest = df_d.iloc[df_d["AvgHours"].idxmax()]
        fastest = df_d.iloc[df_d["AvgHours"].idxmin()]

        st.error(f"⚠️ **Identified Bottleneck (Slowest):** **{slowest['Department']}** ({slowest['AvgHours']:.2f} hrs)")
        st.success(f"⚡ **Most Efficient Stage (Fastest):** **{fastest['Department']}** ({fastest['AvgHours']:.2f} hrs)")
    else:
        st.warning("Not enough complete stage data (or zero duration) to calculate stage completion times.")
else:
    st.warning("No stage duration data available. Ensure all production stage timestamps are being recorded.")
