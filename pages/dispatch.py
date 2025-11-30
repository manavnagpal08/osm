import streamlit as st
from firebase import read, update
from datetime import datetime

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "dispatch"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🚚 Dispatch Department")
st.write("Handle packaging & delivery of completed orders.")

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders = read("orders")

if not orders or not isinstance(orders, dict):
    st.info("No orders found.")
    st.stop()

dispatch_orders = {
    key: data for key, data in orders.items()
    if isinstance(data, dict) and data.get("stage") == "Dispatch"
}

if not dispatch_orders:
    st.info("🎉 No orders in Dispatch stage.")
    st.stop()

# -------------------------------------
# DISPLAY EACH ORDER
# -------------------------------------
for key, order in dispatch_orders.items():

    with st.expander(f"🚚 {order['order_id']} - {order['customer']}", expanded=False):

        st.write(f"**Product:** {order['item']}")
        st.write(f"**Quantity:** {order['qty']}")
        st.write(f"**Due Date:** {order['due']}")

        st.divider()

        packets = st.number_input(
            "How many packets/bundles were created?",
            min_value=1, value=order.get("packets", 1),
            key=f"packets_{key}"
        )

        send_by = st.selectbox(
            "Shipping Method",
            ["Courier", "Self Pickup", "Delivery Van"],
            key=f"shipby_{key}"
        )

        deliver_note = st.text_area(
            "Dispatch Remarks (e.g., bad code, return, etc.)",
            key=f"dbad_{key}"
        )

        st.divider()

        if st.button(f"Mark as Completed ({order['order_id']})", key=f"completedis_{key}"):

            update(f"orders/{key}", {
                "packets": packets,
                "sent_by": send_by,
                "dispatch_note": deliver_note,
                "dispatched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stage": "Completed"
            })

            st.success(f"Order {order['order_id']} marked as DISPATCHED 🎉")
            st.rerun()

