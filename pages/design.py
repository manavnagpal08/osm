import streamlit as st
from firebase import read, update
from datetime import datetime

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department")
st.write("Manage orders in the Design stage.")

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders = read("orders")

if not orders or not isinstance(orders, dict):
    st.info("No orders found.")
    st.stop()

design_orders = {
    key: data for key, data in orders.items()
    if isinstance(data, dict) and data.get("stage") == "Design"
}

if not design_orders:
    st.info("🎉 No orders currently in Design stage.")
    st.stop()

# -------------------------------------
# DISPLAY EACH ORDER
# -------------------------------------
for key, order in design_orders.items():

    with st.expander(f"📝 {order['order_id']} - {order['customer']}", expanded=False):

        st.write(f"**Product:** {order['item']}")
        st.write(f"**Quantity:** {order['qty']}")
        st.write(f"**Due Date:** {order['due']}")

        st.divider()

        # Designer Assign
        assigned_to = st.text_input(
            f"Assign Designer ({order['order_id']})",
            value=order.get("assigned_designer", "")
        )

        # Upload Reference File
        ref_file = st.file_uploader(
            f"Upload Reference Design ({order['order_id']})",
            type=["png", "jpg", "jpeg", "pdf"],
            key=f"file_{key}"
        )

        # Track start/complete times
        if "started_at" in order:
            st.success(f"⏳ Started at: {order['started_at']}")

        # Buttons in a row
        col1, col2 = st.columns(2)

        with col1:
            if st.button(f"Start Design ({order['order_id']})", key=f"start_{key}"):
                update(f"orders/{key}", {
                    "assigned_designer": assigned_to,
                    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("Design started!")
                st.experimental_rerun()

        with col2:
            if st.button(f"Complete & Move to Printing ({order['order_id']})", key=f"done_{key}"):

                # Prepare data update
                update_data = {
                    "assigned_designer": assigned_to,
                    "stage": "Printing",
                    "design_completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # Save reference file as base64 or name (simple)
                if ref_file:
                    update_data["reference_file_name"] = ref_file.name

                update(f"orders/{key}", update_data)

                st.success(f"Order {order['order_id']} moved to Printing Department!")
                st.experimental_rerun()
