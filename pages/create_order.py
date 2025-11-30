import streamlit as st
from firebase import read, push
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

# Load all orders first
all_orders = read("orders") or {}

# ------------------------------------------
# STEP 1 — ORDER TYPE FIRST
# ------------------------------------------
order_type = st.selectbox("Order Type", ["New", "Repeat"])

st.divider()

# ------------------------------------------
# STEP 2 — CUSTOMER SELECTION
# ------------------------------------------

# Extract unique customer names from past orders
customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

customer = None
previous_order = None

if order_type == "New":
    customer = st.text_input("Enter Customer Name")

else:  # Repeat order
    st.subheader("Select Customer")

    if customer_list:
        customer = st.selectbox("Customer", customer_list)
    else:
        st.warning("No existing customers found.")
        st.stop()

    # Once customer selected → fetch previous orders
    customer_orders = {
        key: o for key, o in all_orders.items()
        if isinstance(o, dict) and o.get("customer") == customer
    }

    if customer_orders:
        st.subheader("Select Previous Order to Auto-Fill")
        selected_order = st.selectbox(
            "Previous Orders",
            [f"{o['order_id']} — {o['item']}" for o in customer_orders.values()]
        )

        # Identify the selected previous order
        for k, v in customer_orders.items():
            if selected_order.startswith(v["order_id"]):
                previous_order = v
                break

    else:
        st.warning("No previous orders found for this customer.")
        st.stop()

st.divider()

# ------------------------------------------
# STEP 3 — AUTO-FILLED PRODUCT FIELDS
# ------------------------------------------

order_id = generate_order_id()
st.text_input("Order ID", order_id, disabled=True)

# Product type
product_type = st.selectbox(
    "Product Type", 
    ["Bag", "Box"], 
    index=["Bag","Box"].index(previous_order.get("product_type","Bag")) if previous_order else 0
)

priority = st.selectbox(
    "Priority",
    ["High", "Medium", "Low"],
    index=["High","Medium","Low"].index(previous_order.get("priority","Medium")) if previous_order else 1
)

item = st.text_area(
    "Product Description",
    value=previous_order["item"] if previous_order else ""
)

qty = st.number_input("Quantity", min_value=1)

col1, col2 = st.columns(2)
with col1:
    receive_date = st.date_input("Order Received Date")
with col2:
    due_date = st.date_input("Due Date")

advance = st.radio("Advance Received?", ["Yes", "No"])

st.subheader("Specification Details")

foil = st.text_input("Foil Printing ID",
                     value=previous_order.get("foil_id","") if previous_order else "")

spotuv = st.text_input("Spot UV ID",
                       value=previous_order.get("spotuv_id","") if previous_order else "")

brand_thickness = st.text_input("Brand Thickness ID",
                                value=previous_order.get("brand_thickness_id","") if previous_order else "")

paper_thickness = st.text_input("Paper Thickness ID",
                                value=previous_order.get("paper_thickness_id","") if previous_order else "")

size = st.text_input("Size ID",
                     value=previous_order.get("size_id","") if previous_order else "")

rate = st.number_input("Rate",
                       value=float(previous_order.get("rate",0)) if previous_order else 0.0)

# ------------------------------------------
# STEP 4 — SAVE ORDER
# ------------------------------------------

if st.button("Create Order", type="primary", use_container_width=True):

    if not customer or not item:
        st.error("⚠️ Customer name and item are required.")
        st.stop()

    next_route = "DieCut" if product_type == "Box" else "Assembly"

    data = {
        "order_id": order_id,
        "customer": customer,
        "type": order_type,
        "product_type": product_type,
        "priority": priority,

        "item": item,
        "qty": qty,
        "received": str(receive_date),
        "due": str(due_date),
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
    st.balloons()
