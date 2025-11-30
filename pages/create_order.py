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
st.caption("Efficiently log new and repeat customer orders with auto-fill capabilities.")

# ------------------------------------------
# LOAD REAL ORDERS FROM FIREBASE
# ------------------------------------------
all_orders = read("orders") or {}

customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None

# ------------------------------------------
# FORM STARTS
# ------------------------------------------
with st.form("new_order_form", clear_on_submit=True):

    order_id = generate_order_id()
    st.text_input("Order ID (Auto-Generated)", order_id, disabled=True)

    tab1, tab2, tab3 = st.tabs(["👤 Customer & Order Type", "📝 Product Details", "📐 Specifications & Rate"])

    # -------------------------------
    # TAB 1 — CUSTOMER + ORDER TYPE
    # -------------------------------
    with tab1:
        order_type = st.radio("New or Repeat Order?", ["New", "Repeat"], horizontal=True)

        previous_order_data = None
        customer = None

        if order_type == "New":
            customer = st.text_input("Customer Name")
        else:
            if customer_list:
                customer = st.selectbox("Select Customer", customer_list)
            else:
                st.warning("No customers found. Create a new order first.")
                customer = None

            if customer:
                customer_orders = {
                    k: o for k, o in all_orders.items()
                    if isinstance(o, dict) and o.get("customer") == customer
                }

                if customer_orders:
                    sorted_orders = sorted(customer_orders.values(),
                                           key=lambda x: x.get("received", "0000-00-00"),
                                           reverse=True)

                    options = [f"{o['order_id']} — {o['item']} (Rec: {o['received']})" for o in sorted_orders]
                    selected_display = st.selectbox("Select Previous Order", ["Select"] + options)

                    if selected_display != "Select":
                        selected_id = selected_display.split("—")[0].strip()
                        for o in sorted_orders:
                            if o["order_id"] == selected_id:
                                previous_order_data = o
                                break

        st.session_state["previous_order"] = previous_order_data

    previous_order = st.session_state["previous_order"]

    # -------------------------------
    # TAB 2 — PRODUCT DETAILS
    # -------------------------------
    with tab2:
        default_item = previous_order.get("item", "") if previous_order else ""
        default_product_type = previous_order.get("product_type", "Bag") if previous_order else "Bag"
        default_priority = previous_order.get("priority", "Medium") if previous_order else "Medium"
        default_qty = int(previous_order.get("qty", 100)) if previous_order else 100

        col1, col2, col3 = st.columns(3)
        with col1:
            product_type = st.selectbox("Product Type", ["Bag", "Box"],
                                        index=["Bag","Box"].index(default_product_type))
        with col2:
            qty = st.number_input("Quantity", min_value=1, value=default_qty)
        with col3:
            priority = st.selectbox("Priority", ["High", "Medium", "Low"],
                                    index=["High","Medium","Low"].index(default_priority))

        item = st.text_area("Product Description", value=default_item, height=100)

        col1d, col2d = st.columns(2)
        with col1d:
            receive_date = st.date_input("Order Received Date", value=date.today())
        with col2d:
            default_due = date.today()
            if previous_order and previous_order.get("due"):
                try:
                    default_due = date.fromisoformat(previous_order["due"])
                except:
                    pass
            due_date = st.date_input("Due Date", value=default_due)

        advance_default = 0 if previous_order and previous_order.get("advance") == "Yes" else 1
        advance = st.radio("Advance Received?", ["Yes", "No"], index=advance_default, horizontal=True)

    # -------------------------------
    # TAB 3 — SPECIFICATIONS
    # -------------------------------
    with tab3:

        foil = st.text_input("Foil Printing ID", value=previous_order.get("foil_id","") if previous_order else "")
        brand_thickness = st.text_input("Brand Thickness ID",
                                        value=previous_order.get("brand_thickness_id","") if previous_order else "")
        size = st.text_input("Size ID", value=previous_order.get("size_id","") if previous_order else "")

        spotuv = st.text_input("Spot UV ID", value=previous_order.get("spotuv_id","") if previous_order else "")
        paper_thickness = st.text_input("Paper Thickness ID",
                                        value=previous_order.get("paper_thickness_id","") if previous_order else "")

        default_rate = float(previous_order.get("rate", 0.0)) if previous_order else 0.0
        rate = st.number_input("Rate (per unit)", value=default_rate, min_value=0.0, format="%.2f")

    # -------------------------------
    # SUBMIT
    # -------------------------------
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

            try:
                push("orders", data)
                st.success(f"Order {order_id} created successfully!")
                st.balloons()
            except Exception as e:
                st.error(str(e))
