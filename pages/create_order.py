import streamlit as st
from firebase import push, read
from utils import generate_order_id

# ------------------------------------------
# ROLE CHECK
# ------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Order")

order_id = generate_order_id()
st.text_input("Order ID", order_id, disabled=True)

# Fetch all old orders for repeat selection
all_orders = read("orders") or {}

# ------------------------------------------
# NEW FIELDS: PRODUCT TYPE + PRIORITY
# ------------------------------------------
product_type = st.selectbox("Product Type", ["Bag", "Box"])
priority = st.selectbox("Priority", ["High", "Medium", "Low"])

# ------------------------------------------
# CUSTOMER NAME
# ------------------------------------------
customer = st.text_input("Customer Name")

# ------------------------------------------
# ORDER TYPE: NEW / REPEAT
# ------------------------------------------
order_type = st.selectbox("Order Type", ["New", "Repeat"])

# ------------------------------------------
# REPEAT ORDER AUTOFILL SECTION
# ------------------------------------------
previous_order = None

if order_type == "Repeat":

    # Filter previous orders for SAME customer
    customer_orders = {
        key: data for key, data in all_orders.items()
        if isinstance(data, dict) and data.get("customer", "").lower() == customer.lower()
    }

    if customer_orders:
        st.info("Select a previous order to auto-fill details:")
        selected = st.selectbox(
            "Previous Orders",
            [f"{v['order_id']} - {v['item']}" for v in customer_orders.values()]
        )

        # Find the selected order data
        for k, v in customer_orders.items():
            if selected.startswith(v["order_id"]):
                previous_order = v
                break

    else:
        st.warning("No previous orders found for this customer.")

# ------------------------------------------
# MAIN PRODUCT DETAILS
# ------------------------------------------
st.subheader("Product Details")

item = st.text_area("Product Description", 
                    value=previous_order["item"] if previous_order else "")

qty = st.number_input("Quantity", min_value=1)

col1, col2 = st.columns(2)
with col1:
    receive_date = st.date_input("Order Received Date")
with col2:
    due_date = st.date_input("Due Date")

advance = st.radio("Advance Received?", ["Yes", "No"])

# ------------------------------------------
# OPTIONAL FIELDS (AUTOFILL IF REPEAT)
# ------------------------------------------
st.subheader("Specification Details")

foil = st.text_input("Foil Printing ID", 
                     value=previous_order.get("foil_id", "") if previous_order else "")

spotuv = st.text_input("Spot UV ID", 
                       value=previous_order.get("spotuv_id", "") if previous_order else "")

brand_thickness = st.text_input("Brand Thickness ID", 
                                value=previous_order.get("brand_thickness_id", "") if previous_order else "")

paper_thickness = st.text_input("Paper Thickness ID", 
                                value=previous_order.get("paper_thickness_id", "") if previous_order else "")

size = st.text_input("Size ID", 
                     value=previous_order.get("size_id", "") if previous_order else "")

rate = st.number_input("Rate", min_value=0.0, 
                       value=float(previous_order.get("rate", 0)) if previous_order else 0.0)

# ------------------------------------------
# SUBMIT ORDER
# ------------------------------------------
if st.button("Create Order", type="primary", use_container_width=True):

    if not customer or not item:
        st.error("⚠️ Fill required fields.")
        st.stop()

    # BAG → skip DieCut
    # BOX → must go to DieCut
    next_route = "DieCut" if product_type == "Box" else "Assembly"

    data = {
        "order_id": order_id,
        "customer": customer,
        "product_type": product_type,
        "priority": priority,
        "item": item,
        "qty": qty,
        "received": str(receive_date),
        "due": str(due_date),
        "type": order_type,
        "advance": advance,

        # Specs
        "foil_id": foil,
        "spotuv_id": spotuv,
        "brand_thickness_id": brand_thickness,
        "paper_thickness_id": paper_thickness,
        "size_id": size,
        "rate": rate,

        # Workflow
        "stage": "Design",
        "next_after_printing": next_route
    }

    push("orders", data)
    st.success(f"Order {order_id} created successfully!")
    st.balloons()
