import streamlit as st
from firebase import read, push
from utils import generate_order_id
from datetime import date

st.set_page_config(layout="wide", page_title="Create Order", page_icon="📦")

# ------------------------------------------
# ROLE CHECK
# ------------------------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Manufacturing Order")
st.caption("Log new and repeat orders with instant auto-fill.")

# ------------------------------------------
# LOAD ORDERS FROM FIREBASE
# ------------------------------------------
all_orders = read("orders") or {}

customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

# Keep previous order reference
if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None

# ======================================================================
# STEP 1 — ORDER TYPE & CUSTOMER SELECTION (LIVE)
# ======================================================================

st.subheader("STEP 1 — Order Type & Customer Selection")

colA, colB = st.columns(2)

with colA:
    order_type = st.radio("Order Type", ["New", "Repeat"], horizontal=True)

with colB:
    if order_type == "New":
        customer = st.text_input("Customer Name")
        customer_phone = st.text_input("Customer Phone Number")
        customer_email = st.text_input("Customer Email Address")

    else:
        customer = st.selectbox("Select Customer", ["Select"] + customer_list)

        if customer == "Select":
            customer = None
            customer_phone = ""
            customer_email = ""
        else:
            # Autofill phone & email from last order
            cust_orders = {
                k: o for k, o in all_orders.items()
                if isinstance(o, dict) and o.get("customer") == customer
            }

            if cust_orders:
                latest = sorted(
                    cust_orders.values(),
                    key=lambda o: o.get("received", "0000-00-00"),
                    reverse=True
                )[0]

                customer_phone = latest.get("customer_phone", "")
                customer_email = latest.get("customer_email", "")
            else:
                customer_phone = ""
                customer_email = ""

        st.text_input("Customer Phone Number", value=customer_phone, key="phone_box")
        st.text_input("Customer Email Address", value=customer_email, key="email_box")

# ======================================================================
# STEP 2 — REPEAT ORDER PREVIOUS SELECTION
# ======================================================================

previous_order = None

if order_type == "Repeat" and customer:
    st.subheader("STEP 2 — Choose Previous Order to Auto-Fill")

    customer_orders = {
        k: o for k, o in all_orders.items()
        if isinstance(o, dict) and o.get("customer") == customer
    }

    if customer_orders:
        sorted_orders = sorted(
            customer_orders.values(),
            key=lambda o: o.get("received", "0000-00-00"),
            reverse=True
        )

        options = [
            f"{o['order_id']} — {o['item']} (Rec: {o['received']})"
            for o in sorted_orders
        ]

        selected_display = st.selectbox("Previous Order", ["Select"] + options)

        if selected_display != "Select":
            selected_id = selected_display.split("—")[0].strip()
            for o in sorted_orders:
                if o["order_id"] == selected_id:
                    previous_order = o
                    break

st.session_state["previous_order"] = previous_order

# ======================================================================
# STEP 3 — MAIN FORM (FINAL SUBMISSION)
# ======================================================================

with st.form("order_form"):

    st.subheader("STEP 3 — Enter Order Details")

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = st.session_state.get("previous_order")

    # -------- Product Details ----------
    col1, col2, col3 = st.columns(3)

    with col1:
        product_type = st.selectbox(
            "Product Type",
            ["Bag", "Box"],
            index=["Bag","Box"].index(prev["product_type"]) if prev else 0
        )

    with col2:
        qty = st.number_input(
            "Quantity",
            min_value=1,
            value=int(prev["qty"]) if prev else 100
        )

    with col3:
        priority = st.selectbox(
            "Priority",
            ["High", "Medium", "Low"],
            index=["High","Medium","Low"].index(prev["priority"]) if prev else 1
        )

    item = st.text_area(
        "Product Description",
        value=prev["item"] if prev else "",
        height=100
    )

    colD, colE = st.columns(2)
    with colD:
        receive_date = st.date_input("Received Date", value=date.today())

    with colE:
        default_due = date.today()
        if prev and prev.get("due"):
            try:
                default_due = date.fromisoformat(prev["due"])
            except:
                pass

        due_date = st.date_input("Due Date", value=default_due)

    advance = st.radio(
        "Advance Received?",
        ["Yes", "No"],
        index=0 if prev and prev.get("advance") == "Yes" else 1,
        horizontal=True
    )

    # ---- SPECIFICATIONS ----
    st.subheader("Specifications")

    foil = st.text_input("Foil ID", value=prev.get("foil_id","") if prev else "")
    spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id","") if prev else "")
    brand_thickness = st.text_input("Brand Thickness ID", value=prev.get("brand_thickness_id","") if prev else "")
    paper_thickness = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id","") if prev else "")
    size = st.text_input("Size ID", value=prev.get("size_id","") if prev else "")
    rate = st.number_input("Rate", value=float(prev.get("rate", 0.0)) if prev else 0.0)

    submitted = st.form_submit_button("Create Order")

    if submitted:
        if not customer:
            st.error("Customer name required.")
        elif not item.strip():
            st.error("Product description required.")
        else:

            next_stage = "DieCut" if product_type == "Box" else "Assembly"

            data = {
                "order_id": order_id,
                "customer": customer,

                "customer_phone": customer_phone,
                "customer_email": customer_email,

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
                "rate": float(rate),

                "stage": "Design",
                "next_after_printing": next_stage
            }

            push("orders", data)

            st.success(f"Order {order_id} created successfully!")
            st.info(f"Customer: {customer} | Phone: {customer_phone} | Email: {customer_email}")
            st.balloons()
