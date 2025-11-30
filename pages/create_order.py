import streamlit as st
from firebase import push, read
from utils import generate_order_id

# -----------------------------
# ROLE CHECK
# -----------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Order")

order_id = generate_order_id()
st.text_input("Order ID", order_id, disabled=True)

# -----------------------------
# New Fields: PRODUCT TYPE + PRIORITY
# -----------------------------
product_type = st.selectbox("Product Type", ["Bag", "Box"])
priority = st.selectbox("Priority", ["High", "Medium", "Low"])

# -----------------------------
# ORDER FIELDS
# -----------------------------
customer = st.text_input("Customer Name")
item = st.text_area("Product Description")
qty = st.number_input("Quantity", min_value=1)

col1, col2 = st.columns(2)
with col1:
    receive_date = st.date_input("Order Received Date")
with col2:
    due_date = st.date_input("Due Date")

new_or_repeat = st.selectbox("Order Type", ["New", "Repeat"])
advance = st.radio("Advance Received?", ["Yes", "No"])

# Optional fields
foil = st.text_input("Foil Printing ID (optional)")
spotuv = st.text_input("Spot UV ID (optional)")
brand_thickness = st.text_input("Brand Thickness ID (optional)")
paper_thickness = st.text_input("Paper Thickness ID (optional)")
size = st.text_input("Size ID (optional)")
rate = st.number_input("Rate (optional)", min_value=0.0)

# -----------------------------
# SUBMIT ORDER
# -----------------------------
if st.button("Create Order", type="primary", use_container_width=True):

    if not customer or not item:
        st.error("⚠️ Fill all required fields")
        st.stop()

    # For BAG -> next stage after Printing → Assembly
    # For BOX -> next stage after Printing → DieCut
    next_route = "DieCut" if product_type == "Box" else "Assembly"

    data = {
        "order_id": order_id,
        "product_type": product_type,
        "priority": priority,
        "customer": customer,
        "item": item,
        "qty": qty,
        "received": str(receive_date),
        "due": str(due_date),
        "type": new_or_repeat,
        "advance": advance,
        "foil_id": foil,
        "spotuv_id": spotuv,
        "brand_thickness_id": brand_thickness,
        "paper_thickness_id": paper_thickness,
        "size_id": size,
        "rate": rate,
        "stage": "Design",
        "next_after_printing": next_route
    }

    push("orders", data)
    st.success(f"Order {order_id} created successfully!")
