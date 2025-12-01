import streamlit as st
import pandas as pd
import plotly.express as px
from firebase import read, update, delete # Assuming 'firebase' module handles connection
from datetime import datetime, timezone
import base64
import io

# --- CONFIGURATION ---
DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
FIREBASE_TIMEZONE = timezone.utc # Assuming Firebase stores UTC timestamps

# ------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------------

def get_current_firebase_time_str():
    """Returns the current UTC time in ISO format for Firebase storage."""
    # Use 'Z' for Zulu/UTC time
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def to_datetime_utc(x):
    """Converts ISO format string to UTC timezone aware datetime object."""
    if not x:
        return None
    try:
        # Handles both standard ISO and the 'Z' format used in get_current_firebase_time_str
        dt = datetime.fromisoformat(x.replace('Z', '+00:00'))
        # Ensure it's timezone-aware (it should be if fromisoformat handles the timezone info)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # Fallback for naive timestamps, treat as UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def format_display_date(dt_utc):
    """Formats a UTC datetime object for display in local time."""
    if dt_utc is None:
        return "N/A"
    try:
        # Convert to local timezone for display (Streamlit usually runs on a server)
        # Using a fixed format for clarity
        return dt_utc.astimezone().strftime(DATE_FORMAT)
    except Exception:
        return str(dt_utc)


# ------------------------------------------------------------------------------------
# ADMIN ACCESS & PAGE SETUP
# ------------------------------------------------------------------------------------
st.set_page_config(page_title="🔥 Advanced Orders Admin Panel", layout="wide")

if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Access Denied — Admin Only")
    st.stop()

st.title("🛡️ Admin — Orders Management & Advanced Analytics")
st.markdown("---")


# ------------------------------------------------------------------------------------
# LOAD & PRE-PROCESS ORDERS
# ------------------------------------------------------------------------------------

@st.cache_data(ttl=60) # Cache the data for 60 seconds
def load_and_process_orders():
    """Loads orders from Firebase and performs initial data cleaning."""
    orders = read("orders") or {}
    data = []
    for key, o in orders.items():
        if isinstance(o, dict):
            o["firebase_id"] = key
            data.append(o)

    df = pd.DataFrame(data)

    if df.empty:
        return pd.DataFrame()

    # Define the production stages in order
    production_stages = [
        "Received", "Design", "Printing", "Lamination",
        "DieCut", "Assembly", "Storage", "Dispatch", "Completed"
    ]

    # Map stage to the completion timestamp field
    stage_times = {
        "Received": "received", # Use 'received' as the starting point
        "Design": "design_completed_at",
        "Printing": "printing_completed_at",
        "Lamination": "lamination_completed_at",
        "DieCut": "diecut_completed_at",
        "Assembly": "assembly_completed_at",
        "Storage": "storage_completed_at",
        "Dispatch": "dispatch_completed_at",
        "Completed": "dispatch_completed_at", # Assuming final completion is dispatch
    }

    # Data Quality: Convert all time fields to UTC datetime objects
    for key in stage_times.values():
        if key in df.columns:
            df[key] = df[key].apply(to_datetime_utc)

    # Calculate Time-In-Stage (Advanced Metric)
    df["time_in_stage_sec"] = None
    for i in range(1, len(production_stages)):
        current_stage = production_stages[i]
        prev_stage = production_stages[i-1]
        
        # Determine the columns for start and end time
        end_col = stage_times.get(current_stage)
        start_col = stage_times.get(prev_stage)
        
        if end_col and start_col and end_col in df.columns and start_col in df.columns:
            # Calculate duration for orders that are currently in the *current_stage*
            # This is complex, so for simplicity, we calculate the time *to complete* the previous stage,
            # using the timestamp difference.
            duration = (df[end_col] - df[start_col]).dt.total_seconds()
            
            # Apply to orders that have both timestamps and are at or past the current stage
            mask = df[end_col].notna() & df[start_col].notna()
            df.loc[mask, f"{prev_stage}_duration_hours"] = duration / 3600
            
    # Add display columns for better table view
    df["Received_Display"] = df["received"].apply(lambda x: x.strftime("%d/%m/%Y") if x else "N/A")
    df["Due_Display"] = df["due"].apply(lambda x: x.strftime("%d/%m/%Y") if x else "N/A")


    return df, stage_times, production_stages


df, stage_times, production_stages = load_and_process_orders()

if df.empty:
    st.warning("No orders found in the system.")
    st.stop()

# ------------------------------------------------------------------------------------
# KPI Cards
# ------------------------------------------------------------------------------------
st.markdown("## 🎯 Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Orders", len(df))
col2.metric("Completed Orders", len(df[df["stage"] == "Completed"]))
col3.metric("Active Orders", len(df[df["stage"] != "Completed"]), 
            delta=f"{len(df[df['stage'] != 'Completed'])/len(df)*100:.1f}% of Total")
col4.metric("Orders This Month", 
            len(df[df["received"].astype(str).str[:7] == datetime.now().strftime("%Y-%m")]))
col5.metric("Avg Order Qty", f"{df['qty'].mean():.0f}" if 'qty' in df else "N/A")

st.markdown("---")

# ------------------------------------------------------------------------------------
# SEARCH & FILTERS
# ------------------------------------------------------------------------------------
st.markdown("## 🔍 Order Search and Filtering")
with st.expander("Filter Options"):
    c1, c2, c3 = st.columns(3)

    search = c1.text_input("Search Order ID / Customer Name / Phone", key="search_input")
    
    # Use the full defined stage list for filtering
    stage_filter = c2.selectbox(
        "Filter by Production Stage",
        ["All"] + production_stages,
        key="stage_filter_select"
    )
    priority_filter = c3.selectbox(
        "Filter by Priority",
        ["All", "High", "Medium", "Low"],
        key="priority_filter_select"
    )

df_filtered = df.copy()

if search:
    # Use .str.contains for better, case-insensitive search across key columns
    search_cols = ["order_id", "customer", "customer_phone"]
    df_filtered = df_filtered[
        df_filtered[search_cols].astype(str).apply(
            lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
        )
    ]


if stage_filter != "All":
    df_filtered = df_filtered[df_filtered["stage"] == stage_filter]

if priority_filter != "All":
    df_filtered = df_filtered[df_filtered["priority"] == priority_filter]


# ------------------------------------------------------------------------------------
# TABLE VIEW & ACTIONS
# ------------------------------------------------------------------------------------
st.markdown("## 📋 Filtered Orders Table")

df_display = df_filtered[[
    "order_id", "customer", "customer_phone", "item", "qty",
    "stage", "priority", "Received_Display", "Due_Display", "firebase_id"
]].rename(columns={
    "Received_Display": "Received Date",
    "Due_Display": "Due Date",
    "customer_phone": "Phone"
})

st.dataframe(
    df_display,
    use_container_width=True,
    column_config={
        "firebase_id": st.column_config.Column(
            "ID (FBase)", help="Firebase unique ID.", visible=False
        )
    }
)

colA, colB, colC = st.columns([1, 1, 3])

csv_export = df_filtered.to_csv(index=False).encode()
colA.download_button(
    "📥 Export Filtered Data to CSV", csv_export, "orders_filtered_export.csv", "text/csv"
)

# Advanced Action: Delete All (Hidden behind confirmation)
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
            st.cache_data.clear() # Clear cache after write
            st.rerun()

st.markdown("---")

# ------------------------------------------------------------------------------------
# PER-ORDER DETAILS, EDITING & STAGE UPDATE (Advanced Feature)
# ------------------------------------------------------------------------------------
st.markdown("## 🛠️ Per-Order Management")

selected_order_id = st.selectbox(
    "Select Order ID for Detailed View and Management",
    ["Select"] + df_filtered["order_id"].tolist(),
    key="selected_order_for_detail"
)

if selected_order_id != "Select":
    order_data = df[df["order_id"] == selected_order_id].iloc[0]
    firebase_id = order_data['firebase_id']

    st.markdown(f"### 🧾 Order: **{order_data['order_id']}** (Firebase ID: `{firebase_id}`)")
    
    col_det1, col_det2, col_edit = st.columns([1, 1, 1.5])

    # --- Static Details ---
    with col_det1:
        st.markdown("**Core Details**")
        st.write(f"**Item:** {order_data['item']}")
        st.write(f"**Qty:** {order_data['qty']}")
        st.write(f"**Received:** {format_display_date(order_data.get('received'))}")
        st.write(f"**Due Date:** {format_display_date(to_datetime_utc(order_data.get('due')))}")
    
    # --- Edit Form ---
    with col_edit:
        st.markdown("**Order Update**")
        with st.form("edit_order_form", clear_on_submit=False):
            # Editable Fields
            new_customer = st.text_input("Customer Name", order_data.get('customer', ''), key="edit_cust")
            new_phone = st.text_input("Phone", order_data.get('customer_phone', ''), key="edit_phone")
            new_priority = st.selectbox("Priority", ["High", "Medium", "Low"], 
                                        index=["High", "Medium", "Low"].index(order_data.get('priority', 'Medium')), key="edit_priority")

            # Stage Update Control (The most advanced feature here)
            current_stage_index = production_stages.index(order_data.get('stage', 'Received'))
            new_stage = st.selectbox("Update Production Stage", production_stages, 
                                     index=current_stage_index, key="edit_stage")

            submit_button = st.form_submit_button("💾 Save Updates and Stage")

            if submit_button:
                update_data = {
                    "customer": new_customer,
                    "customer_phone": new_phone,
                    "priority": new_priority,
                }
                
                # Logic for stage update and timestamp recording
                if new_stage != order_data.get('stage'):
                    # Update the stage
                    update_data["stage"] = new_stage
                    
                    # Record the completion timestamp if it's a defined completed stage
                    completion_field = stage_times.get(new_stage)
                    if completion_field and completion_field != "received" and completion_field not in order_data or order_data.get(completion_field) is None:
                         # Only set time if it doesn't exist already
                         update_data[completion_field] = get_current_firebase_time_str()
                         st.success(f"Stage updated to **{new_stage}** and completion time recorded.")
                    else:
                         st.success(f"Stage updated to **{new_stage}**.")

                # Update data in Firebase
                update(f"orders/{firebase_id}", update_data)
                st.cache_data.clear()
                st.rerun()


    # --- QR Code & Delete Button ---
    with col_det2:
        st.markdown("**QR Code & Management**")
        if order_data.get("order_qr"):
            try:
                raw_qr = base64.b64decode(order_data["order_qr"])
                st.image(raw_qr, caption="Order QR Code", width=180)
            except Exception:
                st.error("Could not decode QR image.")
        else:
            st.warning("No QR Code available.")

        # Delete Button (must be outside the form)
        if st.button("🗑️ Delete This Order", key="delete_single_order_btn"):
            delete(f"orders/{firebase_id}")
            st.success(f"Order {selected_order_id} deleted.")
            st.cache_data.clear()
            st.rerun()


    # --- Timeline Chart ---
    st.markdown("### 🕒 Production Timeline")
    tl_data = []
    
    # Calculate time-in-stage for this specific order
    for i in range(1, len(production_stages)):
        current_stage_name = production_stages[i]
        prev_stage_name = production_stages[i-1]
        
        end_time_col = stage_times.get(current_stage_name)
        start_time_col = stage_times.get(prev_stage_name)

        start_time = order_data.get(start_time_col)
        end_time = order_data.get(end_time_col)

        # Record completion time for timeline visualization
        if end_time:
            tl_data.append({"Event": f"{current_stage_name} Completed", "Time": end_time})
        
        # Record Time-in-Stage
        if start_time and end_time:
             duration_seconds = (end_time - start_time).total_seconds()
             tl_data.append({
                 "Event": f"Time in {prev_stage_name}", 
                 "Time": start_time + (end_time - start_time)/2, # Use midpoint for better display
                 "Duration_Hours": duration_seconds / 3600
             })

    if tl_data:
        df_tl = pd.DataFrame(tl_data).sort_values("Time")
        
        fig_tl = px.timeline(
            df_tl.dropna(subset=['Duration_Hours']), # Use only duration bars for Gantt-like view
            x_start=df_tl.dropna(subset=['Duration_Hours'])["Time"] - pd.to_timedelta(df_tl.dropna(subset=['Duration_Hours'])['Duration_Hours'], unit='h') / 2, # Calculate start time
            x_end=df_tl.dropna(subset=['Duration_Hours'])["Time"] + pd.to_timedelta(df_tl.dropna(subset=['Duration_Hours'])['Duration_Hours'], unit='h') / 2, # Calculate end time
            y="Event",
            color="Event",
            title=f"Order Production Flow (ID: {order_data['order_id']})",
            height=400,
        )
        # Add completion point markers
        fig_tl.add_scatter(
            x=df_tl["Time"], 
            y=df_tl["Event"], 
            mode='markers', 
            name='Completion Point',
            marker=dict(symbol='circle-open', size=10, color='black'),
            showlegend=False
        )

        st.plotly_chart(fig_tl, use_container_width=True)
    else:
        st.info("No production timeline data recorded yet.")

st.markdown("---")

# ------------------------------------------------------------------------------------
# ADVANCED ANALYTICS SECTION
# ------------------------------------------------------------------------------------
st.markdown("## 📈 Advanced Analytics Dashboard")

# Row 1: Production Flow & Distribution
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
    )
    st.plotly_chart(fig_m, use_container_width=True)

# Row 2: Weekly Trend & Product Type
col_an3, col_an4 = st.columns(2)

# Weekly Production Trend
with col_an3:
    st.markdown("### 🗓️ Weekly Production Trend")
    # Using the date component of the received time
    df["received_date"] = df["received"].dt.date
    df_weekly = df.groupby("received_date").size().reset_index(name="count")
    
    fig_w = px.line(
        df_weekly,
        x="received_date",
        y="count",
        title="Daily Order Volume Trend",
        labels={"received_date": "Date", "count": "Order Count"},
        markers=True
    )
    st.plotly_chart(fig_w, use_container_width=True)

# Product type pie chart
with col_an4:
    if "product_type" in df:
        st.markdown("### 📦 Product Type Distribution")
        fig_p = px.pie(
            df,
            names="product_type",
            title="Product Type Distribution",
            hole=.4
        )
        st.plotly_chart(fig_p, use_container_width=True)
    else:
        st.info("Product Type distribution is not available (missing 'product_type' column).")

# Row 3: Department Time Analysis (Advanced - Bottleneck Identification)
st.markdown("### ⏱️ Bottleneck Analysis: Average Time to Complete Stage (Hours)")

# Calculate the average duration for each completion column
stage_duration_cols = [c for c in df.columns if c.endswith('_duration_hours')]

if stage_duration_cols:
    
    # Calculate the mean of all stage duration columns
    dept_times_avg = df[stage_duration_cols].mean().reset_index()
    dept_times_avg.columns = ["Duration_Column", "AvgHours"]
    
    # Clean up column names for display
    dept_times_avg["Department"] = dept_times_avg["Duration_Column"].str.replace('_duration_hours', '')

    df_d = dept_times_avg.dropna()

    if not df_d.empty:
        fig_d = px.bar(
            df_d.sort_values("AvgHours", ascending=False), # Sort to clearly show bottlenecks
            x="Department",
            y="AvgHours",
            title="Average Stage Completion Time (Hours)",
            color="AvgHours", # Color by time
            color_continuous_scale=px.colors.sequential.Sunset,
        )
        st.plotly_chart(fig_d, use_container_width=True)

        slowest = df_d.iloc[df_d["AvgHours"].idxmax()]
        fastest = df_d.iloc[df_d["AvgHours"].idxmin()]

        st.error(f"⚠️ **Identified Bottleneck (Slowest):** **{slowest['Department']}** ({slowest['AvgHours']:.2f} hrs)")
        st.success(f"⚡ **Most Efficient Stage (Fastest):** **{fastest['Department']}** ({fastest['AvgHours']:.2f} hrs)")
    else:
        st.warning("Not enough data to calculate stage completion times.")
else:
    st.warning("No stage duration data available (Are timestamps recorded?).")

st.markdown("---")

# Offer a next step
st.markdown("Need to analyze a specific bottleneck? **Select a stage in the filter above** to examine only the orders currently stuck there.")
