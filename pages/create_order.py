import streamlit as st
from firebase import read, push
from utils import generate_order_id
from datetime import date

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

# ------------- ROLE CHECK -------------
if "role" not in st.session_state:
    st.session_state["role"] = "design"

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Manufacturing Order")
st.caption("Effortlessly log new and repeat orders with smart auto-fill capability.")

# ------------- LOAD ORDERS -------------
all_orders = read("orders") or {}

customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None


# =====================================================
# STEP 1 — ORDER TYPE & CUSTOMER
# =====================================================
main_container = st.container(border=True)

with main_container:
    st.subheader("1️⃣ Order Type & Customer Selection")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        order_type = st.radio(
            "Select Order Type",
            ["New Order 🆕", "Repeat Order 🔄"],
            horizontal=True
        )
        order_type_simple = "New" if order_type == "New Order 🆕" else "Repeat"

    with col2:
        customer = None
        customer_phone = ""
        customer_email = ""

        if order_type_simple == "New":
            customer = st.text_input("Customer Name (Required)")
            customer_phone = st.text_input("Customer Phone Number")
            customer_email = st.text_input("Customer Email Address")

        else:
            selected = st.selectbox("Select Customer", ["Select"] + customer_list)

            if selected != "Select":
                customer = selected

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

                st.text_input("Customer Phone Number", value=customer_phone, key="ph")
                st.text_input("Customer Email Address", value=customer_email, key="em")


# =====================================================
# STEP 2 — PREVIOUS ORDER (Repeat Only)
# =====================================================
previous_order = None

if order_type_simple == "Repeat" and customer:
    st.markdown("<br>", unsafe_allow_html=True)

    cust_orders = {
        k: o for k, o in all_orders.items()
        if isinstance(o, dict) and o.get("customer") == customer
    }

    if cust_orders:
        st.subheader("2️⃣ Select Previous Order to Auto-Fill")

        sorted_orders = sorted(
            cust_orders.values(),
            key=lambda o: o.get("received", "0000-00-00"),
            reverse=True
        )

        options = [
            f"{o['order_id']} — {o['item']} (Rec: {o['received']})"
            for o in sorted_orders
        ]

        selected_display = st.selectbox(
            "Pick Order",
            ["--- Select ---"] + options
        )

        if selected_display != "--- Select ---":
            selected_id = selected_display.split("—")[0].strip()
            for o in sorted_orders:
                if o["order_id"] == selected_id:
                    previous_order = o
                    st.success("✨ Auto-fill applied!")
                    break

st.session_state["previous_order"] = previous_order


# =====================================================
# STEP 3 — MAIN FORM
# =====================================================
with st.form("order_form", clear_on_submit=True):

    st.header("3️⃣ Order Specification Form")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID", order_id, disabled=True)

    prev = st.session_state.get("previous_order") or {}  # FIXED

    tab1, tab2 = st.tabs(["📋 General & Timeline", "📐 Specification IDs & Rate"])

    # ---------------- TAB 1 ----------------
    with tab1:
        colA, colB, colC = st.columns(3)

        with colA:
            product_type = st.selectbox(
                "Product Type",
                ["Bag", "Box"],
                index=["Bag", "Box"].index(prev.get("product_type", "Bag"))
                if prev.get("product_type") in ["Bag", "Box"] else 0
            )

        with colB:
            qty = st.number_input(
                "Quantity",
                min_value=1,
                value=int(prev.get("qty", 100))
            )

        with colC:
            priority = st.selectbox(
                "Priority",
                ["High", "Medium", "Low"],
                index=["High", "Medium", "Low"].index(prev.get("priority", "Medium"))
                if prev.get("priority") in ["High", "Medium", "Low"] else 1
            )

        item = st.text_area(
            "Product Description",
            value=prev.get("item", ""),
            height=100
        )

        colD, colE = st.columns(2)
        with colD:
            receive_date = st.date_input("Received Date", value=date.today())
        with colE:
            default_due = date.today()
            if prev.get("due"):
                try:
                    default_due = date.fromisoformat(prev["due"])
                except:
                    pass
            due_date = st.date_input("Due Date", value=default_due)

        advance = st.radio(
            "Advance Received?",
            ["Yes", "No"],
            index=0 if prev.get("advance") == "Yes" else 1,
            horizontal=True
        )

    # ---------------- TAB 2 ----------------
    with tab2:
        colF, colG = st.columns(2)

        with colF:
            foil = st.text_input("Foil ID", value=prev.get("foil_id", ""))
            brand_thickness = st.text_input("Brand Thickness ID", value=prev.get("brand_thickness_id", ""))
            size = st.text_input("Size ID", value=prev.get("size_id", ""))

        with colG:
            spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id", ""))
            paper_thickness = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id", ""))

            rate = st.number_input(
                "Unit Rate (₹)",
                min_value=0.0,
                value=float(prev.get("rate", 0.0)),
                format="%.2f"
            )

        total_value = float(qty) * float(rate)
        st.metric("💰 Total Value", f"₹{total_value:,.2f}")


    # ------------- SUBMIT BUTTON (FIXED) -------------
    submitted = st.form_submit_button("🚀 Create Order", type="primary")

    if submitted:
        if not customer:
            st.error("Customer name missing.")
        elif not item.strip():
            st.error("Product description required.")
        elif receive_date > due_date:
            st.error("Invalid dates.")
        else:

            next_stage = "DieCut" if product_type == "Box" else "Assembly"

            data = {
                "order_id": order_id,
                "customer": customer,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                "type": order_type_simple,
                "product_type": product_type,
                "priority": priority,
                "item": item.strip(),
                "qty": int(qty),
                "received": str(receive_date),
                "due": str(due_date),
                "advance": advance,
                "foil_id": foil.strip(),
                "spotuv_id": spotuv.strip(),
                "brand_thickness_id": brand_thickness.strip(),
                "paper_thickness_id": paper_thickness.strip(),
                "size_id": size.strip(),
                "rate": float(rate),
                "stage": "Design",
                "next_after_printing": next_stage
            }

            push("orders", data)
            st.success(f"🎉 Order {order_id} created successfully!")
            st.balloons()
