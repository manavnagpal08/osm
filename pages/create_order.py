import streamlit as st
from firebase import read, push
from utils import generate_order_id
from datetime import date

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

# ------------------------------------------
# ROLE CHECK
# ------------------------------------------
if "role" not in st.session_state:
    # st.switch_page("pages/login.py")
    # MOCKING LOGIN FOR DEMO
    st.session_state["role"] = "design"

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Manufacturing Order")
st.caption("Log new and repeat customer orders with automatic data retrieval and auto-fill.")

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
# UI SECTION 1: ORDER TYPE & CUSTOMER SELECTION (LIVE)
# ======================================================================

with st.container(border=True):
    st.subheader("1️⃣ Order Type & Customer Identification")
    st.markdown("---")
    
    colA, colB = st.columns([1, 2])

    with colA:
        order_type = st.radio("Order Type", ["New", "Repeat"], horizontal=True, help="New orders require manual input; Repeat orders allow auto-fill.")
    
    with colB:
        customer = None
        customer_phone = ""
        customer_email = ""

        if order_type == "New":
            st.markdown("**Enter New Customer Details**")
            customer = st.text_input("Customer Name", key="new_cust_name", placeholder="e.g., Global Textiles Ltd.")
            
            # Use columns for compact phone/email input in New Order flow
            colP, colE = st.columns(2)
            with colP:
                customer_phone = st.text_input("Customer Phone Number", key="new_phone", placeholder="+1-555-1234")
            with colE:
                customer_email = st.text_input("Customer Email Address", key="new_email", placeholder="contact@global.com")

        else: # Repeat Order
            st.markdown("**Select Existing Customer**")
            customer_select = st.selectbox("Select Customer Name", ["Select"] + customer_list, key="repeat_cust_select")

            if customer_select == "Select":
                customer = None
            else:
                customer = customer_select
                
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
                
                # Display and allow editing of autofilled contact info
                colP_r, colE_r = st.columns(2)
                with colP_r:
                    st.text_input("Customer Phone Number (Autofilled)", value=customer_phone, key="phone_box", help="Edit if contact details have changed.")
                with colE_r:
                    st.text_input("Customer Email Address (Autofilled)", value=customer_email, key="email_box", help="Edit if contact details have changed.")

# ======================================================================
# UI SECTION 2: REPEAT ORDER PREVIOUS SELECTION (LIVE)
# ======================================================================

previous_order = None

if order_type == "Repeat" and customer:
    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    with st.container(border=True):
        st.subheader("2️⃣ Load Previous Order for Auto-Fill")
        st.info("Select a past order to quickly populate product details below.")
        
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
                f"#{o['order_id']} — {o['item']} (Rec: {o['received']})"
                for o in sorted_orders
            ]

            selected_display = st.selectbox(
                "Select Previous Order to Clone", 
                ["--- Select Order to Load Data ---"] + options,
                key="prev_order_select"
            )

            if selected_display != "--- Select Order to Load Data ---":
                selected_id = selected_display.split("—")[0].strip().replace('#', '')
                for o in sorted_orders:
                    if o["order_id"] == selected_id:
                        previous_order = o
                        st.success("✅ Order details ready for auto-fill in Step 3.")
                        break
            else:
                st.session_state["previous_order"] = None
        else:
            st.warning(f"No previous orders found for **{customer}**.")

st.session_state["previous_order"] = previous_order

st.markdown("<br>", unsafe_allow_html=True) # Spacer
st.divider()

# ======================================================================
# UI SECTION 3: MAIN FORM (FINAL SUBMISSION)
# ======================================================================

with st.form("order_form", clear_on_submit=True):

    st.header("3️⃣ Final Order Specification")
    
    # --- Auto-fill logic variables ---
    # Use empty dict as default for prev to avoid KeyErrors
    prev = st.session_state.get("previous_order", {})
    
    # --- Get current contact info (handles both New and Repeat keys) ---
    if order_type == "New":
        # Pull from new entry boxes
        final_customer_phone = st.session_state.get("new_phone", "")
        final_customer_email = st.session_state.get("new_email", "")
    else:
        # Pull from repeat entry boxes (which are autofilled)
        final_customer_phone = st.session_state.get("phone_box", "")
        final_customer_email = st.session_state.get("email_box", "")


    # --- TABS FOR BETTER UI ---
    tab1, tab2 = st.tabs(["📝 Product & Timeline", "📐 Specifications & Rate"])
    
    with tab1:
        st.subheader("Core Product Details")
        
        col_id, _, _ = st.columns(3)
        with col_id:
            order_id = generate_order_id()
            st.text_input("Order ID (Auto-Generated)", order_id, disabled=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            product_type = st.selectbox(
                "Product Type",
                ["Bag", "Box"],
                index=["Bag","Box"].index(prev.get("product_type", "Bag")) if prev.get("product_type") in ["Bag", "Box"] else 0
            )

        with col2:
            qty = st.number_input(
                "Quantity",
                min_value=1,
                value=int(prev.get("qty", 100))
            )

        with col3:
            priority = st.selectbox(
                "Priority",
                ["High", "Medium", "Low"],
                index=["High","Medium","Low"].index(prev.get("priority", "Medium")) if prev.get("priority") in ["High", "Medium", "Low"] else 1
            )

        item = st.text_area(
            "Product Description (Required)",
            value=prev.get("item", ""),
            height=100,
            placeholder="e.g., 5x5x2 Rigid Folding Box, Standard Brown Paper Bag"
        )
        
        st.markdown("---")
        st.subheader("Timeline & Payment")
        
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
            due_date = st.date_input("Due Date (Target Completion)", value=default_due)

        advance = st.radio(
            "Advance Payment Received?",
            ["Yes", "No"],
            index=0 if prev.get("advance") == "Yes" else 1,
            horizontal=True
        )

    with tab2:
        st.subheader("Specification IDs & Pricing")
        st.info("Use these fields to record material and process IDs from design archives.")
        
        # Group specs into two vertical columns for better screen usage
        colF, colG = st.columns(2)
        
        with colF:
            foil = st.text_input("Foil ID", value=prev.get("foil_id",""), placeholder="e.g., F-101")
            brand_thickness = st.text_input("Brand Thickness ID", value=prev.get("brand_thickness_id",""), placeholder="e.g., BT-250GSM")
            size = st.text_input("Size ID (Dimensions)", value=prev.get("size_id",""), placeholder="e.g., S-30x20x10cm")

        with colG:
            spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id",""), placeholder="e.g., UV-500")
            paper_thickness = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id",""), placeholder="e.g., PT-120GSM")
            
            rate = st.number_input(
                "Rate (Unit Price ₹)", 
                min_value=0.0, 
                value=float(prev.get("rate", 0.0)),
                format="%.2f"
            )

        st.markdown("---")
        # Final calculation feedback
        total_value = float(qty) * float(rate)
        st.metric(
            label="💰 Estimated Total Order Value (Quantity × Rate)", 
            value=f"₹{total_value:,.2f}"
        )


    submitted = st.form_submit_button("🚀 Finalize and Create Order", type="primary", use_container_width=True)

    if submitted:
        # Final validation
        if not customer:
            st.error("❌ **Customer name is required.** Please complete Step 1.")
        elif not item.strip():
            st.error("❌ **Product description is required.** Please complete Tab 1.")
        elif receive_date > due_date:
            st.error("❌ **Due Date cannot be before the Received Date.** Please check your dates in Tab 1.")
        else:
            # Data preparation
            next_stage = "DieCut" if product_type == "Box" else "Assembly"
            
            # Use final cleaned contact fields from the submission scope
            data = {
                "order_id": order_id,
                "customer": customer,
                "customer_phone": final_customer_phone, # Use values from session state / keys
                "customer_email": final_customer_email, # Use values from session state / keys
                "type": order_type,
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

            try:
                push("orders", data)
                st.success(f"✅ Order **{order_id}** created successfully and routed to the **Design** stage!")
                st.info(f"Customer: **{customer}** | Phone: {final_customer_phone} | Email: {final_customer_email}")
                st.balloons()
                st.session_state["previous_order"] = None # Clear previous selection
            except Exception as e:
                st.exception(f"An error occurred while saving to the database: {e}")
