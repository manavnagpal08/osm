import streamlit as st
from firebase import read, update
from datetime import datetime

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "diecut"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("✂️ Die-Cut Department")
st.write("Manage orders in Die-Cut stage.")

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders = read("orders")

if not orders or not isinstance(orders, dict):
    st.info("No orders found.")
    st.stop()

diecut_orders = {
    key: data for key, data in orders.items()
    if isinstance(data, dict) and data.get("stage") == "DieCut"
}

if not diecut_orders:
    st.info("🎉 No orders in Die-Cut stage.")
    st.stop()

# -------------------------------------
# DISPLAY EACH ORDER
# -------------------------------------
for key, order in diecut_orders.items():

    with st.expander(f"✂️ {order['order_id']} - {order['customer']}", expanded=False):

        st.write(f"**Product:** {order['item']}")
        st.write(f"**Quantity:** {order['qty']}")
        st.write(f"**Total Sheets:** {order.get('total_sheets', 'N/A')}")
        st.write(f"**Due:** {order['due']}")

        st.divider()

        # Assign operator
        operator = st.text_input(
            f"Assign Die-Cut Machine Operator ({order['order_id']})",
            value=order.get("diecut_operator", "")
        )

        machine = st.selectbox(
            "Cutting Machine",
            ["Auto Die Machine", "Manual Die Machine", "Laser Cutter"],
            key=f"machine_{key}"
        )

        special_note = st.text_area("Special Instructions (optional)", key=f"note_{key}")

        st.divider()

        # Start time
        if order.get("diecut_started_at"):
            st.success(f"⏳ Started at: {order['diecut_started_at']}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(f"Start Die-Cut ({order['order_id']})", key=f"startdie_{key}"):
                update(f"orders/{key}", {
                    "diecut_operator": operator,
                    "diecut_machine": machine,
                    "special_note": special_note,
                    "diecut_started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                st.success("Die-Cut started!")
                st.rerun()

        with col2:
            if st.button(f"Complete & Move to Assembly ({order['order_id']})", key=f"donedie_{key}"):

                update(f"orders/{key}", {
                    "diecut_operator": operator,
                    "diecut_machine": machine,
                    "special_note": special_note,
                    "diecut_completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stage": "Assembly"
                })

                st.success(f"Order {order['order_id']} moved to Assembly!")
                st.rerun()

