import streamlit as st
from firebase import read, update
from datetime import datetime

# -------------------------------------
# ROLE CHECK
# -------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "printing"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("🖨️ Printing Department")
st.write("Manage orders currently in the Printing stage.")

# -------------------------------------
# FETCH ORDERS
# -------------------------------------
orders = read("orders")

if not orders or not isinstance(orders, dict):
    st.info("No orders found.")
    st.stop()

printing_orders = {
    key: data for key, data in orders.items()
    if isinstance(data, dict) and data.get("stage") == "Printing"
}

if not printing_orders:
    st.info("🎉 No orders currently in the Printing stage.")
    st.stop()

# -------------------------------------
# DISPLAY EACH PRINTING ORDER
# -------------------------------------
for key, order in printing_orders.items():

    with st.expander(f"🖨️ {order['order_id']} - {order['customer']}", expanded=False):

        st.write(f"**Product:** {order['item']}")
        st.write(f"**Quantity:** {order['qty']}")
        st.write(f"**Due Date:** {order['due']}")

        st.divider()

        # Assign operator
        operator = st.text_input(
            f"Assign Printing Operator ({order['order_id']})",
            value=order.get("assigned_printer", "")
        )

        # Upload print artwork
        art_file = st.file_uploader(
            f"Upload Artwork for Printing ({order['order_id']})",
            type=["png", "jpg", "jpeg", "pdf"],
            key=f"art_{key}"
        )

        # -----------------------------
        # SHEET CALCULATION
        # -----------------------------
        st.subheader("📄 Sheet Calculation")

        col1, col2 = st.columns(2)
        with col1:
            sheets_per_unit = st.number_input(
                "Sheets required per unit?",
                min_value=1, value=1, key=f"sheetper_{key}"
            )
        with col2:
            total_sheets = sheets_per_unit * int(order["qty"])
            st.number_input("Total Sheets Needed", value=total_sheets, disabled=True)

        st.write(f"➡️ **Total Sheets to Print: {total_sheets} sheets**")

        # Paper wastage category
        wastage = st.selectbox(
            "Paper Wastage Category",
            ["Low (2%)", "Medium (5%)", "High (10%)"],
            key=f"wastage_{key}"
        )

        finish_type = st.selectbox(
            "Finish Type",
            ["Gloss", "Matte", "Soft-Touch", "None"],
            key=f"finish_{key}"
        )

        st.divider()

        # Show start time if exists
        if order.get("printing_started_at"):
            st.success(f"⏳ Started at: {order['printing_started_at']}")

        colA, colB = st.columns(2)

        # START PRINTING
        with colA:
            if st.button(f"Start Printing ({order['order_id']})", key=f"startprint_{key}"):

                update(f"orders/{key}", {
                    "assigned_printer": operator,
                    "printing_started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "finish_type": finish_type,
                    "wastage": wastage,
                    "total_sheets": total_sheets,
                })

                st.success("🔄 Printing started!")
                st.experimental_rerun()

        # COMPLETE PRINTING & MOVE STAGE
        with colB:
            if st.button(f"Complete & Move to Die-Cut ({order['order_id']})", key=f"completeprint_{key}"):

                update_data = {
                    "assigned_printer": operator,
                    "stage": "DieCut",
                    "printing_completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "finish_type": finish_type,
                    "wastage": wastage,
                    "total_sheets": total_sheets,
                }

                if art_file:
                    update_data["artwork_file_name"] = art_file.name

                update(f"orders/{key}", update_data)

                st.success(f"Order {order['order_id']} moved to Die-Cut Department!")
                st.experimental_rerun()

