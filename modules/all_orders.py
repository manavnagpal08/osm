import streamlit as st
import pandas as pd
import plotly.express as px
from firebase import read, update, delete 
from datetime import datetime, timezone, date, timedelta
import time
import numpy as np 
from dateutil import parser 

# --- CONFIGURATION ---
DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
FIREBASE_TIMEZONE = timezone.utc 

# ------------------------------------------------------------------------------------
# HELPER FUNCTIONS (UNCHANGED)
# ------------------------------------------------------------------------------------

def get_current_firebase_time_str():
    """Returns the current UTC time in ISO format for Firebase storage."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def to_datetime_utc(x):
    """Converts ISO format string to UTC timezone aware datetime object."""
    if not x:
        return None
    try:
        dt = parser.isoparse(str(x).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def calculate_priority_score(row):
    """
    Calculates a numerical priority score based on Priority and Time to Deadline.
    Higher score means more critical.
    """
    score_map = {"High": 3, "Medium": 2, "Low": 1}
    base_score = score_map.get(row.get('priority', 'Low'), 1)
    
    time_to_deadline = row.get('Time_To_Deadline', 100)
    
    if time_to_deadline < 0:
        modifier = 100 + abs(time_to_deadline) * 5 
    elif time_to_deadline <= 3:
        modifier = (3 - time_to_deadline) * 2
    else:
        modifier = 0
        
    return base_score + modifier

# ------------------------------------------------------------------------------------
# STICKY FILTER AND SELECTION LOGIC (UNCHANGED)
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
        current_val = st.query_params.get(key)
        if current_val != str(value):
            st.query_params[key] = str(value)
    except Exception as e:
        pass

def set_selected_order(firebase_id):
    """Sets the selected order ID in the query parameters and reruns."""
    set_sticky_filter_state("selected_order_id", firebase_id)
    st.rerun()

# ------------------------------------------------------------------------------------
# ADMIN ACCESS & PAGE SETUP (UNCHANGED)
# ------------------------------------------------------------------------------------

st.set_page_config(page_title="🚀 Supercharged Production Dashboard", layout="wide") 

if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Access Denied — Admin Only")
    st.stop()

# ------------------------------------------------------------------------------------
# LOAD & PRE-PROCESS ORDERS (UNCHANGED)
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

    all_time_keys = list(set(stage_times.values()) | set(['due']))
    
    for key in all_time_keys:
        if key in df.columns:
            df[key] = pd.to_datetime(df[key].apply(to_datetime_utc), utc=True, errors='coerce')
        else:
            df[key] = pd.NaT 

    df["Qty"] = df.get('qty', pd.Series()).fillna(0).astype(int)
    df["Due_Date"] = df['due'].dt.date.replace({pd.NaT: None})
    
    current_time = datetime.now(timezone.utc)
    time_delta = df['due'] - current_time
    df['Time_To_Deadline'] = (time_delta.dt.total_seconds() / (24 * 3600)).round(1).fillna(100) 

    df['Priority_Score'] = df.apply(calculate_priority_score, axis=1)

    for i in range(1, len(production_stages)):
        prev_stage = production_stages[i-1]
        start_col = stage_times.get(prev_stage)
        end_col = stage_times.get(production_stages[i])

        if start_col in df.columns and end_col in df.columns:
            duration_timedelta = (df[end_col] - df[start_col])
            duration_seconds = duration_timedelta.dt.total_seconds().fillna(0)
            df[f"{prev_stage}_duration_hours"] = (duration_seconds / 3600).round(2)

    if 'firebase_id' not in df.columns:
         df['firebase_id'] = np.nan
        
    return df, stage_times, production_stages


df, stage_times, production_stages = load_and_process_orders()

# ------------------------------------------------------------------------------------
# ACTION FUNCTIONS (UPDATED FOR BULK)
# ------------------------------------------------------------------------------------

def quick_advance_stage(current_firebase_id, current_stage):
    """Advances a single order to the next stage and logs the timestamp."""
    
    current_index = production_stages.index(current_stage)
    if current_index < len(production_stages) - 1:
        next_stage = production_stages[current_index + 1]
    else:
        # If already at the last stage, return without updating
        return f"Order is already at the final stage: **{current_stage}**", False

    timestamp_key = stage_times.get(next_stage)
    update_data = {
        "stage": next_stage,
        timestamp_key: get_current_firebase_time_str()
    }

    update(f"orders/{current_firebase_id}", update_data)
    return f"Advanced to **{next_stage}**.", True

def bulk_advance_orders(firebase_ids):
    """Advances multiple orders one stage forward."""
    successful_updates = 0
    for fid in firebase_ids:
        # Fetch current stage for the order (necessary for the advance logic)
        current_stage = df[df['firebase_id'] == fid]['stage'].iloc[0]
        
        _, success = quick_advance_stage(fid, current_stage)
        if success:
            successful_updates += 1
            
    st.toast(f"✅ Successfully advanced **{successful_updates}** orders to the next stage!", icon='🚀')
    st.cache_data.clear() 
    set_sticky_filter_state("selected_order_id", "") 
    st.rerun()

def bulk_update_priority(firebase_ids, new_priority):
    """Updates the priority for multiple orders."""
    for fid in firebase_ids:
        update(f"orders/{fid}", {'priority': new_priority})
            
    st.toast(f"✅ Successfully set priority to **{new_priority}** for **{len(firebase_ids)}** orders.", icon='🌟')
    st.cache_data.clear() 
    set_sticky_filter_state("selected_order_id", "") 
    st.rerun()

def save_order_updates(firebase_id, order_id, new_priority, new_qty, new_due_date):
    """Saves updates for a single order."""
    update_data = {
        'priority': new_priority,
        'qty': int(new_qty),
    }

    if new_due_date:
        try:
            dt_obj = datetime(new_due_date.year, new_due_date.month, new_due_date.day, 23, 59, 59, tzinfo=timezone.utc)
            update_data['due'] = dt_obj.isoformat().replace('+00:00', 'Z')
        except Exception:
            st.error(f"Invalid date format for order **{order_id}**. Date not updated.")
            return

    update(f"orders/{firebase_id}", update_data)
    st.toast(f"💾 Updated Order ID: **{order_id}** details.", icon='⚙️')
    st.cache_data.clear() 
    set_sticky_filter_state("selected_order_id", "")
    st.rerun()

# ------------------------------------------------------------------------------------
# PAGE LAYOUT START
# ------------------------------------------------------------------------------------

st.title("🛡️ Admin — Orders Management & Advanced Analytics")
st.markdown("---")

if df.empty:
    st.warning("No orders found in the system.")
    st.stop()
    
# --- KPI BLOCK ---
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("**Total Orders**", len(df))
col2.metric("**Completed Orders**", len(df[df["stage"] == "Completed"]))
col3.metric("**Active Orders**", len(df[df["stage"] != "Completed"]), 
            delta=f"{len(df[df['stage'] != 'Completed'])/len(df)*100:.1f}% of Total" if len(df) > 0 else "0%")
orders_this_month = len(df[df["received"].dt.strftime("%Y-%m") == datetime.now().strftime("%Y-%m")])
col4.metric("**Orders This Month**", orders_this_month) 
col5.metric("**Avg Priority Score**", f"{df['Priority_Score'].mean():.1f}")

st.markdown("---")

# --- FILTERING ---
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


# Select columns for display 
df_display = df_filtered[[
    "order_id", "customer", "item", "Qty", 
    "stage", "priority", "Due_Date", "Time_To_Deadline", "Priority_Score", "firebase_id"
]].rename(columns={
    "order_id": "Order ID",
    "customer": "Customer",
    "item": "Item",
    "stage": "Stage",
    "priority": "Priority",
    "Time_To_Deadline": "Deadline (Days)",
    "Priority_Score": "Score",
    "firebase_id": "Firebase ID" 
})

# --- ORDER SELECTION AND EDIT FORM (Single Item) ---
selected_order_id = get_sticky_filter_state("selected_order_id", None)

if selected_order_id:
    # --- DEDICATED EDIT FORM (Single-row productivity) ---
    selected_row = df_display[df_display['Firebase ID'] == selected_order_id]
    
    if not selected_row.empty:
        selected_row_data = selected_row.iloc[0]
        st.markdown(f"## 🛠️ Edit & Advance Order: **{selected_row_data['Order ID']}**")
        st.info(f"Current Stage: **{selected_row_data['Stage']}** | Priority: **{selected_row_data['Priority']}** | Score: **{selected_row_data['Score']:.1f}**")
        
        with st.form("edit_order_form", clear_on_submit=False):
            col_e1, col_e2, col_e3 = st.columns(3)
            
            new_priority = col_e1.selectbox(
                "Priority", ["High", "Medium", "Low"],
                index=["High", "Medium", "Low"].index(selected_row_data['Priority']),
                key="edit_priority"
            )
            new_qty = col_e2.number_input(
                "Quantity (Qty)", min_value=0, value=int(selected_row_data['Qty']), key="edit_qty"
            )
            new_due_date = col_e3.date_input(
                "Due Date", 
                value=pd.to_datetime(selected_row_data['Due_Date']).date() if pd.notna(selected_row_data['Due_Date']) else date.today(),
                key="edit_due_date"
            )

            c_actions, c_cancel = st.columns([3, 1])
            
            if c_actions.form_submit_button("💾 Save All Changes (Priority, Qty, Date)", type="primary"):
                save_order_updates(selected_order_id, selected_row_data['Order ID'], new_priority, new_qty, new_due_date)
            
            if c_cancel.form_submit_button("❌ Cancel Edit", type="secondary"):
                set_sticky_filter_state("selected_order_id", "") 
                st.rerun()

        st.markdown("### Quick Actions")
        if st.button("⏩ Advance to Next Stage", help="Move the order one step forward and log the time.", type="warning"):
            quick_advance_stage(selected_order_id, selected_row_data['Stage'])

        st.markdown("---")

    else:
        set_sticky_filter_state("selected_order_id", "") 
        st.rerun()

# --- DISPLAY ORDERS AND BULK ACTIONS ---

st.markdown("## 📋 Order Management Spaces (Select multiple rows for Bulk Actions)")

tab1, tab2, tab3 = st.tabs(["**All Filtered Orders**", "**Pending Orders** ⏳", "**Stored Products** 📦"])

# Initialize session state for selected rows if not present
if 'selected_firebase_ids' not in st.session_state:
    st.session_state['selected_firebase_ids'] = []

def render_selectable_dataframe(df_to_render, key_suffix=""):
    """Renders a dataframe supporting multi-row selection for bulk actions."""
    
    df_render = df_to_render.drop(columns=['Firebase ID'])
    
    # Define styling for urgency
    column_config = {
        "Deadline (Days)": st.column_config.NumberColumn(
            "Deadline (Days)",
            format="%.1f days",
            # Apply styling using Python-native conditional formatting
            help="Negative days means overdue. Click a row for single-item edit."
        ),
    }

    selected_indices_container = st.dataframe(
        df_render,
        hide_index=True,
        use_container_width=True,
        key=f"data_frame_{key_suffix}",
        selection_mode="multi-row", # Changed to MULTI-ROW
        column_order=df_render.columns.tolist(),
        column_config=column_config
    )
    
    # Get the indices of the selected rows in the displayed/rendered dataframe
    selection = selected_indices_container.get('selection')
    if selection and selection.get('rows'):
        selected_positions = selection['rows']
        
        # Map the positional indices back to the unique Firebase IDs
        selected_firebase_ids = df_to_render.iloc[selected_positions]['Firebase ID'].tolist()
        st.session_state['selected_firebase_ids'] = selected_firebase_ids
    else:
        st.session_state['selected_firebase_ids'] = []


with tab1:
    st.markdown("### All Orders (Filtered View)")
    # Sort by Score (descending) by default to show urgent orders first
    render_selectable_dataframe(
        df_display.sort_values(by="Score", ascending=False), 
        key_suffix="all"
    )

with tab2:
    st.markdown("### Pending Production Orders")
    df_pending = df_display[~df_display['Stage'].isin(['Completed', 'Dispatch'])]
    
    if df_pending.empty:
        st.info("🎉 No outstanding orders currently in production!")
    else:
        render_selectable_dataframe(
            df_pending.sort_values(by="Score", ascending=False),
            key_suffix="pending"
        )

with tab3:
    st.markdown("### Products Ready for Dispatch (Storage)")
    df_stored = df_display[df_display['Stage'] == 'Storage']
    
    if df_stored.empty:
        st.info("📦 No products currently awaiting pickup or dispatch in storage.")
    else:
        render_selectable_dataframe(
            df_stored.sort_values(by="Due_Date", ascending=True),
            key_suffix="stored"
        )

# --- BULK ACTIONS PANEL ---
selected_ids = st.session_state.get('selected_firebase_ids', [])

st.markdown("---")
st.markdown("## 🎯 Bulk Actions")

if selected_ids:
    st.success(f"**{len(selected_ids)}** orders selected for bulk actions.")
    
    col_bulk1, col_bulk2, col_bulk3 = st.columns(3)
    
    # Bulk Advance Button
    if col_bulk1.button(f"⏩ Bulk Advance {len(selected_ids)} Orders", type="warning", key="bulk_advance_btn"):
        bulk_advance_orders(selected_ids)
        
    # Bulk Priority Update
    with col_bulk2.form("bulk_priority_form", clear_on_submit=True):
        new_bulk_priority = st.selectbox(
            "Set Priority to:",
            ["High", "Medium", "Low"],
            key="bulk_priority_select"
        )
        if st.form_submit_button(f"🌟 Set Priority for {len(selected_ids)} Orders", type="primary"):
            bulk_update_priority(selected_ids, new_bulk_priority)

    # Bulk Delete (Re-using the delete logic for selected)
    if col_bulk3.button(f"🗑️ Delete {len(selected_ids)} Selected Orders", type="secondary", key="bulk_delete_btn"):
        if st.session_state.get("confirm_delete_bulk") != True:
            st.session_state["confirm_delete_bulk"] = True
            col_bulk3.warning(f"⚠️ Are you sure? Click again to confirm **DELETION OF {len(selected_ids)}** orders.")
        else:
            with st.spinner(f"Deleting {len(selected_ids)} orders..."):
                for fid in selected_ids:
                    delete(f"orders/{fid}")
                st.success(f"**{len(selected_ids)}** selected orders deleted.")
                st.session_state.pop("confirm_delete_bulk", None)
                st.cache_data.clear() 
                st.rerun()
                
else:
    st.info("Select one or more rows in the tables above to enable bulk actions.")

st.markdown("---")

## 📈 Advanced Analytics Dashboard (UNCHANGED)

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
