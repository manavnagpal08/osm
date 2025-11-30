
import streamlit as st
from firebase import read, update

if "role" not in st.session_state:
    st.switch_page("../login.py")

if st.session_state["role"] not in ["admin", "design"]:
    st.error("You do not have permission to access this page.")
    st.stop()

st.title("🎨 Design Department")

orders = read("orders")

if orders:
    for key, order in orders.items():
        if isinstance(order, dict) and order.get("stage") == "Design":
            st.subheader(order["order_id"])

            assign = st.text_input(f"Assigned Designer ({order['order_id']})")

            if st.button(f"Mark Complete {order['order_id']}"):
                update(f"orders/{key}", {
                    "assigned_designer": assign,
                    "stage": "Printing"
                })
                st.success("Moved to Printing")
                st.experimental_rerun()
else:
    st.info("No orders in Design stage.")
