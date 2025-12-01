import streamlit as st
from firebase import read, update, delete
import pandas as pd
import base64
from datetime import datetime, timezone, timedelta
import io

st.set_page_config(page_title="Admin – All Orders", page_icon="🧮", layout="wide")

# ---------------- ROLE CHECK ----------------
if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Only Admin Has Permission To View All Orders.")
    st.stop()

# ---------------- LOAD ORDERS ----------------
orders = read("orders") or {}

# Convert orders into dataframe
df = []
for key, o in orders.items():
    if not isinstance(o, dict):
        continue
    row = o.copy()
    row["key"] = key
    df.append(row)

df = pd.DataFrame(df)

if df.empty:
    st.warning("No orders found in the system.")
    st.stop()

# -------------------------------------------------------------------
# --------------- CLEAN TIMESTAMPS TO DATETIME -----------------------
# -------------------------------------------------------------------
timestamp_fields = [
    "design_completed_at", "printing_completed_at", "lamination_completed_at",
    "diecut_completed_at", "assembly_completed_at", "packaging_completed_at",
    "storage_started_at", "storage_completed_at",
    "dispatch_completed_at", "completed_at"
]

def to_dt(x):
    if pd.isna(x):
        return None
    try:
        dt = datetime.fromisoformat(str(x))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return None

for f in timestamp_fields:
    if f in df.columns:
        df[f] = df[f].apply(to_dt)

# -------------------------------------------------------------------
# ----------------------- KPI COMPUTATION ----------------------------
# -------------------------------------------------------------------
total_orders = len(df)
in_design = (df["stage"] == "Design").sum()
in_print = (df["stage"] == "Printing").sum()
in_lam = (df["stage"] == "Lamination").sum()
in_diecut = (df["stage"] == "Diecut").sum()
in_assembly = (df["stage"] == "Assembly").sum()
in_packaging = (df["stage"] == "Packaging").sum()
in_storage = (df["stage"] == "Storage").sum()
in_dispatch = (df["stage"] == "Dispatch").sum()
completed = (df["stage"] == "Completed").sum()

# compute departmental average times
def duration(start_field, end_field):
    if start_field not in df.columns or end_field not in df.columns:
        return None
    x = df[end_field] - df[start_field]
    x = x.dropna()
    if len(x) == 0:
        return None
    return x.mean()

dept_times = {
    "Design": duration("received", "design_completed_at"),
    "Printing": duration("design_completed_at", "printing_completed_at"),
    "Lamination": duration("printing_completed_at", "lamination_completed_at"),
    "Diecut": duration("lamination_completed_at", "diecut_completed_at"),
    "Assembly": duration("diecut_completed_at", "assembly_completed_at"),
    "Packaging": duration("assembly_completed_at", "packaging_completed_at"),
    "Storage Wait": duration("packaging_completed_at", "storage_started_at"),
    "Dispatch": duration("storage_completed_at", "dispatch_completed_at")
}

# detect slowest department
clean_depts = {k: v for k, v in dept_times.items() if v is not None}
slowest_dept = max(clean_depts, key=lambda x: clean_depts[x]) if clean_depts else "N/A"

# -------------------------------------------------------------------
# ---------------------- KPI DASHBOARD -------------------------------
# -------------------------------------------------------------------
st.title("📊 Admin – All Orders Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Orders", total_orders)
col2.metric("Active Orders", total_orders - completed)
col3.metric("Completed Orders", completed)
col4.metric("Slowest Department", slowest_dept)

st.markdown("### 📌 Orders Per Stage")
st.info(
    f"""
- 🎨 **Design:** {in_design}  
- 🖨 **Printing:** {in_print}  
- 🧪 **Lamination:** {in_lam}  
- ✂ **Diecut:** {in_diecut}  
- 🧩 **Assembly:** {in_assembly}  
- 🎁 **Packaging:** {in_packaging}  
- 🏬 **Storage:** {in_storage}  
- 🚀 **Dispatch:** {in_dispatch}  
- ✅ **Completed:** {completed}
"""
)

# -------------------------------------------------------------------
# ---------------------- FILTER + SEARCH -----------------------------
# -------------------------------------------------------------------
st.subheader("🔍 Search & Filter Orders")

colA, colB, colC = st.columns(3)

search_text = colA.text_input("Search Order ID / Customer / Item")
stage_filter = colB.selectbox("Filter by Stage", ["All"] + sorted(df["stage"].unique()))
priority_filter = colC.selectbox("Priority", ["All", "High", "Medium", "Low"])

filtered = df.copy()

if search_text.strip():
    filtered = filtered[
        filtered["order_id"].str.contains(search_text, case=False, na=False)
        | filtered["customer"].str.contains(search_text, case=False, na=False)
        | filtered["item"].str.contains(search_text, case=False, na=False)
    ]

if stage_filter != "All":
    filtered = filtered[filtered["stage"] == stage_filter]

if priority_filter != "All":
    filtered = filtered[filtered["priority"] == priority_filter]

st.write(f"🔎 Showing {len(filtered)} matching orders")

# -------------------------------------------------------------------
# ---------------------- EXPORT TO CSV -------------------------------
# -------------------------------------------------------------------
csv_bytes = filtered.to_csv(index=False).encode()
st.download_button("📥 Export Filtered Orders to CSV", csv_bytes, "orders.csv", "text/csv")

st.divider()

# -------------------------------------------------------------------
# ---------------------- ORDER TABLE (MAIN) --------------------------
# -------------------------------------------------------------------
st.subheader("📄 All Orders")

for idx, row in filtered.iterrows():
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([3, 1, 2, 1])

        col1.markdown(f"### {row['order_id']} — {row.get('item', '')}")
        col1.caption(f"Customer: {row.get('customer', '')}")

        col2.metric("Qty", row.get("qty", "?"))
        col3.metric("Stage", row.get("stage", "N/A"))
        col4.metric("Priority", row.get("priority", "Medium"))

        # Timeline visualization
        with st.expander("📅 Timeline"):
            for f in timestamp_fields:
                st.write(f"**{f}**: {row.get(f)}")

        # Department durations
        with st.expander("⏱ Stage Durations"):
            for dept, dur in dept_times.items():
                st.write(f"**{dept}:** {dur}")

        # Delete button
        if st.button("🗑 Delete Permanently", key=f"del_{row['key']}"):
            delete(f"orders/{row['key']}")
            st.error("Order Deleted Permanently.")
            st.rerun()

        st.markdown("---")
