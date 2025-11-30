import streamlit as st
from firebase import read, update
from datetime import datetime

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "assembly"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🧩 Assembly Department")
st.write("Manage orders in Assembly stage.")

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders = read("orders")

if not orders or not isinstance(orders, dict):
    st.info("No orders found.")
    st.stop()

assembly_orders = {
    key: data for key, data in orders.items()
    if isinstance(data, dict) and data.get("stage") == "Assembly"
}

if not assembly_orders:
    st.info("🎉 No orders in Assembly stage.")
    st.stop()

# -------------------------------------
# DISPLAY EACH ORDER
# -------------------------------------
for key, order in assembly_orders.items():

    with st.expander(f"🧩 {order['order_id']} - {order['customer']}", expanded=False):

        st.write(f"**Product:** {order['item']}")
        st.write(f"**Quantity:** {order['qty']}")
        st.write(f"**Due Date:** {order['due']}")

        st.divider()

        materials = st.text_area(
            "Materials Used (e.g., Glue, Tape, Inserts, Wrappers)",
            value=order.get("assembly_materials", ""),
            key=f"materials_{key}"
        )

        operator = st.text_input(
            f"Assembly Operator ({order['order_id']})",
            value=order.get("assembly_operator", "")
        )

        special_inst = st.text_area(
            "Special Instructions (optional)",
            value=order.get("assembly_note", ""),
            key=f"assnote_{key}"
        )

        # Start time
        if order.get("assembly_started_at"):
            st.success(f"⏳ Started at: {order['assembly_started_at']}")

        colA, colB = st.columns(2)

        with colA:
            if st.button(f"Start Assembly ({order['order_id']})", key=f"startass_{key}"):
                update(f"orders/{key}", {
                    "assembly_operator": operator,
                    "assembly_materials": materials,
                    "assembly_note": special_inst,
                    "assembly_started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                st.success("Assembly started!")
                st.experimental_rerun()

        with colB:
            if st.button(f"Complete & Move to Dispatch ({order['order_id']})", key=f"doneass_{key}"):

                update(f"orders/{key}", {
                    "assembly_operator": operator,
                    "assembly_materials": materials,
                    "assembly_note": special_inst,
                    "assembly_completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "stage": "Dispatch"
                })

                st.success(f"Order {order['order_id']} moved to Dispatch!")
                st.experimental_rerun()
