import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta, timezone
from firebase import read, delete

st.set_page_config(page_title="All Orders – Admin", page_icon="📊", layout="wide")

# -----------------------------------------------------
# ADMIN CHECK
# -----------------------------------------------------
if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Only admin can view this page.")
    st.stop()

st.title("📊 All Orders – Admin Dashboard")

# -----------------------------------------------------
# LOAD ORDERS
# -----------------------------------------------------
orders = read("orders") or {}

if not orders:
    st.warning("No orders found.")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(orders).T

# Convert timestamps safely
def safe_parse(x):
    if not x or x == "" or pd.isna(x):
        return None
    try:
        d = datetime.fromisoformat(x)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except:
        return None

timestamp_fields = [
    "design_completed_at", "printing_completed_at", "lamination_completed_at",
    "diecut_completed_at", "assembly_completed_at", "packaging_completed_at",
    "storage_started_at", "storage_completed_at", "dispatch_completed_at",
    "completed_at", "received", "due"
]

for f in timestamp_fields:
    if f in df.columns:
        df[f] = df[f].apply(safe_parse)

# -----------------------------------------------------
# SAFE DURATION
# -----------------------------------------------------
def duration(start_field, end_field):
    """Safely compute average duration between two timestamp fields."""
    if start_field not in df.columns or end_field not in df.columns:
        return None

    valid = df[[start_field, end_field]].dropna()
    if valid.empty:
        return None

    diffs = []
    for _, r in valid.iterrows():
        s, e = r[start_field], r[end_field]
        if s is None or e is None:  
            continue
        try:
            diffs.append(e - s)
        except:
            continue

    if not diffs:
        return None

    avg = sum(diffs, timedelta()) / len(diffs)
    return avg

# -----------------------------------------------------
# KPI CARDS
# -----------------------------------------------------
total_orders = len(df)
completed_orders = df["completed_at"].notna().sum()
pending_orders = total_orders - completed_orders

col1, col2, col3 = st.columns(3)
col1.metric("Total Orders", total_orders)
col2.metric("Completed Orders", completed_orders)
col3.metric("Pending Orders", pending_orders)

# -----------------------------------------------------
# DEPARTMENT AVERAGE TIME
# -----------------------------------------------------
dept_times = {
    "Design": duration("received", "design_completed_at"),
    "Printing": duration("design_completed_at", "printing_completed_at"),
    "Lamination": duration("printing_completed_at", "lamination_completed_at"),
    "Diecut": duration("lamination_completed_at", "diecut_completed_at"),
    "Assembly": duration("diecut_completed_at", "assembly_completed_at"),
    "Packaging": duration("assembly_completed_at", "packaging_completed_at"),
    "Storage Wait": duration("packaging_completed_at", "storage_started_at"),
    "Dispatch": duration("storage_completed_at", "dispatch_completed_at"),
}

st.subheader("⏱️ Average Time Taken by Each Department")

dept_df = pd.DataFrame([
    {"Department": k, "Avg Duration": (str(v).split('.')[0] if v else "–")}
    for k, v in dept_times.items()
])

st.dataframe(dept_df, use_container_width=True)

# -----------------------------------------------------
# MONTH-WISE PRODUCTION ANALYSIS
# -----------------------------------------------------
st.subheader("📈 Monthly Production Count")

df["month"] = df["received"].apply(lambda x: x.strftime("%Y-%m") if x else None)
month_counts = df["month"].value_counts().sort_index()

st.bar_chart(month_counts)

# -----------------------------------------------------
# SLOWEST DEPARTMENT FINDER
# -----------------------------------------------------
st.subheader("🐢 Slowest Department (Longest Avg Time)")

valid_times = {k: v for k, v in dept_times.items() if v}
if valid_times:
    slowest = max(valid_times, key=valid_times.get)
    st.warning(f"**Slowest Department:** {slowest} – Avg {str(valid_times[slowest]).split('.')[0]}")
else:
    st.info("Insufficient data for delay analysis.")

# -----------------------------------------------------
# ORDERS TABLE
# -----------------------------------------------------
st.subheader("📋 All Orders Table")

df_display = df.copy()
df_display["received"] = df_display["received"].astype(str)
df_display["due"] = df_display["due"].astype(str)

st.dataframe(df_display, use_container_width=True, height=500)

# -----------------------------------------------------
# EXPORT CSV
# -----------------------------------------------------
csv = df_display.to_csv().encode("utf-8")
st.download_button("⬇ Download Orders CSV", csv, "all_orders.csv", "text/csv")

# -----------------------------------------------------
# DELETE ORDER
# -----------------------------------------------------
st.subheader("🗑 Delete Single Order")

order_ids = df["order_id"].dropna().tolist()
selected_del = st.selectbox("Select Order to Delete", ["Select"] + order_ids)

if selected_del != "Select":
    if st.button("Delete Selected Order", type="primary"):
        # Find key associated with order_id
        for k, v in orders.items():
            if v.get("order_id") == selected_del:
                delete(f"orders/{k}")
                st.success(f"Order {selected_del} deleted.")
                st.rerun()

# -----------------------------------------------------
# DELETE ALL ORDERS (PERMANENT)
# -----------------------------------------------------
st.subheader("🔥 Delete All Orders")

if st.button("Delete ALL Orders (Irreversible)", type="secondary"):
    for k in orders.keys():
        delete(f"orders/{k}")
    st.success("All orders deleted permanently.")
    st.rerun()
