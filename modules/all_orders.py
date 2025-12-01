import streamlit as st
import pandas as pd
import plotly.express as px
# Assuming 'firebase' module handles connection (read, update, delete)
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
        # Return None or a known invalid value if conversion fails
        return None

def calculate_priority_score(row):
    """
    Calculates a numerical priority score based on Priority and Time to Deadline.
    Higher score means more critical.
    """
    score_map = {"High": 3, "Medium": 2, "Low": 1}
    base_score = score_map.get(row.get('priority', 'Low'), 1)
    
    # Use .get() and provide a safe default value if the column is missing/empty
    time_to_deadline = row.get('Time_To_Deadline', 100)
    
    if time_to_deadline < 0:
        modifier = 100 + abs(time_to_deadline) * 5 
    elif time_to_deadline <= 3:
        modifier = (3 - time_to_deadline) * 2
    else:
        modifier = 0
        
    return base_score + modifier

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

st.set_page_config(page_title="🔥 Advanced Orders Admin Panel (Read-Only)", layout="wide") 

if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Access Denied — Admin Only")
    st.stop()

# ------------------------------------------------------------------------------------
# LOAD & PRE-PROCESS ORDERS (The source of the error is stabilized here)
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
            # Errors='coerce' converts bad strings to pd.NaT
            df[key] = pd.to_datetime(df[key].apply(to_datetime_utc), utc=True, errors='coerce')
        else:
            # Add missing timestamp columns filled with NaT to prevent key errors later
            df[key] = pd.NaT 

    # Prepare columns for the display 
    df["Qty"] = df.get('qty', pd.Series()).fillna(0).astype(int)
    
    # Convert Timestamp to a Python date object for display compatibility
    df["Due_Date"] = df['due'].dt.date.replace({pd.NaT: None})
    
    # --- Advanced Metric: Time to Deadline ---
    current_time = datetime.now(timezone.utc)
    time_delta = df['due'] - current_time
    # Safely convert timedelta to days, coercing errors to NaT, then filling NaT for score calc
    df['Time_To_Deadline'] = (time_delta.dt.total_seconds() / (24 * 3600)).round(1).fillna(100) 

    # --- Advanced Feature: Priority Score ---
    df['Priority_Score'] = df.apply(calculate_priority_score, axis=1)

    # Calculate Time-In-Stage
    for i in range(1, len(production_stages)):
        prev_stage = production_stages[i-1]
        
        start_col = stage_times.get(prev_stage)
        end_col = stage_times.get(production_stages[i])

        if start_col in df.columns and end_col in df.columns:
            # CRITICAL FIX: Ensure NaT handling in subtraction. Result is Timedelta or NaT.
            duration_timedelta = (df[end_col] - df[start_col])
            # The .dt accessor is safe here because duration_timedelta is guaranteed to be timedelta64[ns]
            duration_seconds = duration_timedelta.dt.total_seconds().fillna(0)
            df[f"{prev_stage}_duration_hours"] = (duration_seconds / 3600).round(2)


    # Final step: Ensure the Firebase ID column exists, as it is needed for other functions
    if 'firebase_id' not in df.columns:
         df['firebase_id'] = np.nan
        
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

col1.metric("**Total Orders**", len(df))
col2.metric("**Completed Orders**", len(df[df["stage"] == "Completed"]))
col3.metric("**Active Orders**", len(df[df["stage"] != "Completed"]), 
            delta=f"{len(df[df['stage'] != 'Completed'])/len(df)*100:.1f}% of Total" if len(df) > 0 else "0%")
orders_this_month = len(df[df["received"].dt.strftime("%Y-%m") == datetime.now().strftime("%Y-%m")])
col4.metric("**Orders This Month**", orders_this_month) 
col5.metric("**Avg Priority Score**", f"{df['Priority_Score'].mean():.1f}")

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

if df_filtered.empty:
    st.warning("No orders match the current filter criteria.")


# Select columns for display (Read-only)
df_display = df_filtered[[
    "order_id", "customer", "customer_phone", "item", "Qty", 
    "stage", "priority", "Due_Date", "Time_To_Deadline", "Priority_Score" 
]].rename(columns={
    "customer_phone": "Phone",
    "order_id": "Order ID",
    "customer": "Customer",
    "item": "Item",
    "stage": "Stage",
    "priority": "Priority",
    "Time_To_Deadline": "Deadline (Days)",
    "Priority_Score": "Score",
})

# ------------------------------------------------------------------------------------
## 📋 Orders Table Spaces (Read-Only)
# ------------------------------------------------------------------------------------
st.markdown("## 📋 Order Management Spaces")

tab1, tab2, tab3 = st.tabs(["**All Filtered Orders**", "**Pending Orders** ⏳", "**Stored Products** 📦"])

# Tab 1: All Filtered Orders
with tab1:
    st.markdown("### All Orders (Filtered View)")
    st.dataframe(
        df_display,
        hide_index=True,
        use_container_width=True,
    )

# Tab 2: Pending Orders (Not completed or dispatched)
with tab2:
    st.markdown("### Pending Production Orders")
    df_pending = df_display[~df_display['Stage'].isin(['Completed', 'Dispatch'])]
    
    if df_pending.empty:
        st.info("🎉 No outstanding orders currently in production!")
    else:
        st.dataframe(
            df_pending.sort_values(by="Score", ascending=False),
            hide_index=True,
            use_container_width=True,
        )

# Tab 3: Stored Products (In the storage stage)
with tab3:
    st.markdown("### Products Ready for Dispatch (Storage)")
    df_stored = df_display[df_display['Stage'] == 'Storage']
    
    if df_stored.empty:
        st.info("📦 No products currently awaiting pickup or dispatch in storage.")
    else:
        st.dataframe(
            df_stored.sort_values(by="Due_Date", ascending=True),
            hide_index=True,
            use_container_width=True,
        )

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


# Monthly production
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
