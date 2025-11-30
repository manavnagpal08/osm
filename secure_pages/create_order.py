
import streamlit as st
from firebase import push
from utils import generate_order_id

# Role check
if "role" not in st.session_state:
    st.switch_page("login.py")

if st.session_state["role"] not in ["admin", "design"]:
    st.error("You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Order")

order_id = generate_order_id()
st.text_input("Order ID", order_id, disabled=True)

customer = st.text_input("Customer Name")
item = st.text_area("Product Description")
qty = st.number_input("Quantity", min_value=1)
receive_date = st.date_input("Order Received Date")
due_date = st.date_input("Due Date")

new_or_repeat = st.selectbox("Order Type", ["New", "Repeat"])
advance = st.radio("Advance Received?", ["Yes", "No"])

if st.button("Create Order"):
    data = {
        "order_id": order_id,
        "customer": customer,
        "item": item,
        "qty": qty,
        "received": str(receive_date),
        "due": str(due_date),
        "type": new_or_repeat,
        "advance": advance,
        "stage": "Design"
    }
    push("orders", data)
    st.success("Order Created Successfully!")
