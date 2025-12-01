import streamlit as st
import pandas as pd
import plotly.express as px
from firebase import read, update, delete
from datetime import datetime, timezone
import base64
import io

# ------------------------------------------------------------------------------------
# ADMIN ACCESS
# ------------------------------------------------------------------------------------
st.set_page_config(page_title="All Orders Admin Panel", layout="wide")

if "role" not in st.session_state or st.session_state["role"] != "admin":
    st.error("❌ Access Denied — Admin Only")
    st.stop()

st.title("📊 Admin — All Orders Manager & Analytics")

# ------------------------------------------------------------------------------------
# LOAD ORDERS
# ------------------------------------------------------------------------------------
orders = read("orders") or {}

data = []
for key, o in orders.items():
    if isinstance(o, dict):
        o["firebase_id"] = key
        data.append(o)

df = pd.DataFrame(data)

if df.empty:
    st.warning("No orders found in the system.")
    st.stop()

# Convert timestamps if available
def to_dt(x):
    try:
        return datetime.fromisoformat(x) if x else None
    except:
        return None

stage_times = {
    "Design": "design_completed_at",
    "Printing": "printing_completed_at",
    "Lamination": "lamination_completed_at",
    "DieCut": "diecut_completed_at",
    "Assembly": "assembly_completed_at",
    "Storage": "storage_completed_at",
    "Dispatch": "dispatch_completed_at",
}

# ------------------------------------------------------------------------------------
# KPI Cards
# ------------------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Orders", len(df))
col2.metric("Completed Orders", len(df[df["stage"] == "Completed"]))
col3.metric("Active Orders", len(df[df["stage"] != "Completed"]))
col4.metric("Orders This Month", len(df[df["received"].astype(str).str[:7] ==
                                      datetime.now().strftime("%Y-%m")]))

# ------------------------------------------------------------------------------------
# SEARCH & FILTERS
# ------------------------------------------------------------------------------------
with st.expander("🔍 Filters"):
    c1, c2, c3 = st.columns(3)

    search = c1.text_input("Search Order / Customer / Phone")
    stage_filter = c2.selectbox(
        "Filter by Stage",
        ["All"] + sorted(df["stage"].unique().tolist())
    )
    priority_filter = c3.selectbox(
        "Filter by Priority",
        ["All", "High", "Medium", "Low"]
    )

df_filtered = df.copy()

if search:
    df_filtered = df_filtered[
        df_filtered.apply(
            lambda r: search.lower() in str(r).lower(), axis=1
        )
    ]

if stage_filter != "All":
    df_filtered = df_filtered[df_filtered["stage"] == stage_filter]

if priority_filter != "All":
    df_filtered = df_filtered[df_filtered["priority"] == priority_filter]

# ------------------------------------------------------------------------------------
# TABLE VIEW
# ------------------------------------------------------------------------------------
st.subheader("📄 All Orders")

def format_date(d):
    try:
        return datetime.fromisoformat(d).strftime("%d/%m/%Y")
    except:
        return d

df_show = df_filtered.copy()
if "received" in df_show:
    df_show["received"] = df_show["received"].apply(format_date)
if "due" in df_show:
    df_show["due"] = df_show["due"].apply(format_date)

st.dataframe(
    df_show[[
        "order_id", "customer", "customer_phone", "item", "qty",
        "stage", "priority", "received", "due", "firebase_id"
    ]],
    use_container_width=True
)

# ------------------------------------------------------------------------------------
# ACTIONS: EXPORT / DELETE ALL
# ------------------------------------------------------------------------------------
colA, colB = st.columns(2)

csv = df_show.to_csv(index=False).encode()
colA.download_button("📥 Export to CSV", csv, "orders_export.csv", "text/csv")

if colB.button("🗑️ Delete ALL Orders"):
    for key in df["firebase_id"]:
        delete(f"orders/{key}")
    st.success("All orders deleted.")
    st.rerun()

# ------------------------------------------------------------------------------------
# PER-ORDER DETAILS
# ------------------------------------------------------------------------------------
st.subheader("🔎 View Order Details")

selected_order = st.selectbox(
    "Select Order",
    ["Select"] + df_show["order_id"].tolist()
)

if selected_order != "Select":
    order = df[df["order_id"] == selected_order].iloc[0]

    with st.container(border=True):
        st.markdown(f"## 🧾 Order: {order['order_id']}")

        c1, c2 = st.columns(2)
        c1.write(f"**Customer:** {order['customer']}")
        c1.write(f"**Phone:** {order['customer_phone']}")
        c1.write(f"**Product:** {order['item']}")
        c1.write(f"**Priority:** {order['priority']}")
        c1.write(f"**Qty:** {order['qty']}")
        c1.write(f"**Stage:** {order['stage']}")

        raw = base64.b64decode(order["order_qr"])
        st.image(raw, width=180)

        if st.button("🗑️ Delete This Order"):
            delete(f"orders/{order['firebase_id']}")
            st.success("Order deleted.")
            st.rerun()

    # Timeline Chart
    st.markdown("### 🕒 Order Production Timeline")

    tl_data = []
    for dept, key in stage_times.items():
        if key in order and order[key]:
            tl_data.append({"Department": dept, "Completed": to_dt(order[key])})

    if tl_data:
        df_tl = pd.DataFrame(tl_data)

        fig_tl = px.scatter(
            df_tl,
            x="Completed",
            y="Department",
            title="Order Production Timeline",
            height=400
        )
        st.plotly_chart(fig_tl, use_container_width=True)

# ------------------------------------------------------------------------------------
# ANALYTICS SECTION
# ------------------------------------------------------------------------------------
st.subheader("📈 Analytics Dashboard")

# Monthly production
df["month"] = df["received"].astype(str).str[:7]

fig_m = px.bar(
    df.groupby("month").size().reset_index(name="count"),
    x="month",
    y="count",
    title="Monthly Orders",
)
st.plotly_chart(fig_m, use_container_width=True)

# Weekly Production
df["week"] = df["received"].astype(str).str[:10]

fig_w = px.line(
    df.groupby("week").size().reset_index(name="count"),
    x="week",
    y="count",
    title="Weekly Production",
)
st.plotly_chart(fig_w, use_container_width=True)

# Product type pie chart
if "product_type" in df:
    fig_p = px.pie(
        df,
        names="product_type",
        title="Product Type Distribution"
    )
    st.plotly_chart(fig_p, use_container_width=True)

# Time Consumption by Department
st.markdown("### 🏭 Department Time Analysis")

dept_times = {}
for dept, key in stage_times.items():
    if key in df:
        df[key] = df[key].apply(to_dt)
        times = []
        for idx, r in df.iterrows():
            if r.get(key):
                base = to_dt(r.get("received")) or to_dt(r.get("design_completed_at"))
                if base and r[key]:
                    times.append((r[key] - base).total_seconds())
        if times:
            dept_times[dept] = sum(times) / len(times)

if dept_times:
    df_d = pd.DataFrame({
        "Department": list(dept_times.keys()),
        "AvgTimeSec": list(dept_times.values())
    })
    df_d["AvgHours"] = df_d["AvgTimeSec"] / 3600

    fig_d = px.bar(
        df_d,
        x="Department",
        y="AvgHours",
        title="Average Time Taken by Department (Hours)"
    )
    st.plotly_chart(fig_d, use_container_width=True)

    slowest = df_d.iloc[df_d["AvgHours"].idxmax()]
    fastest = df_d.iloc[df_d["AvgHours"].idxmin()]

    st.success(f"⏳ **Most Time Consuming:** {slowest['Department']} ({slowest['AvgHours']:.2f} hrs)")
    st.info(f"⚡ **Fastest Department:** {fastest['Department']} ({fastest['AvgHours']:.2f} hrs)")
