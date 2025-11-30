import streamlit as st
from firebase import read, push
from utils import generate_order_id
from datetime import date

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(layout="wide", page_title="Create Manufacturing Order", page_icon="📦")

# ------------------------------------------
# ROLE CHECK (Keep this section first for security)
# ------------------------------------------
if "role" not in st.session_state:
    # st.switch_page("pages/login.py")
    # MOCKING LOGIN FOR DEMO
    st.session_state["role"] = "design"

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Manufacturing Order")
st.caption("Effortlessly log new and repeat orders with instant auto-fill capability.")

# ------------------------------------------
# LOAD ORDERS FROM FIREBASE
# ------------------------------------------
all_orders = read("orders") or {}

customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

# Initialize previous order data state
if "previous_order" not in st.session_state:
    st.session_state["previous_order"] = None

# --- Main Page Container for Visual Separation ---
main_container = st.container(border=True)

with main_container:
    
    ## 🎯 Step 1: Order Type & Customer Selection
    st.subheader("1️⃣ Order Type & Customer Selection")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        order_type = st.radio(
            "Select Order Type", 
            ["New Order 🆕", "Repeat Order 🔄"], 
            horizontal=True,
            key="order_type_radio"
        )
        # Simplify the variable to match logic below
        order_type_simple = "New" if order_type == "New Order 🆕" else "Repeat"
    
    with col2:
        customer = None
        if order_type_simple == "New":
            customer = st.text_input("Enter Customer Name (Required)", placeholder="e.g., Acme Corp")
        else:
            customer_select = st.selectbox("Select Existing Customer (Required)", ["Select Customer"] + customer_list)
            if customer_select != "Select Customer":
                customer = customer_select

    previous_order = None

    # --- Conditional Lookup Area ---
    if order_type_simple == "Repeat" and customer:
        
        st.markdown("<br>", unsafe_allow_html=True) # Add some visual space
        st.info(f"Loading previous orders for **{customer}**...")

        customer_orders = {
            k: o for k, o in all_orders.items()
            if isinstance(o, dict) and o.get("customer") == customer
        }

        if customer_orders:
            st.subheader("2️⃣ Choose Previous Order to Auto-Fill")

            sorted_orders = sorted(
                customer_orders.values(),
                key=lambda o: o.get("received", "0000-00-00"),
                reverse=True
            )

            # Beautified display option
            options = [f"#{o['order_id']} — {o['item']} (Rec: {o['received']})"
                       for o in sorted_orders]

            selected_display = st.selectbox(
                "Select a Previous Order to Auto-Fill Details (Optional)",
                ["--- Select Order ---"] + options
            )

            if selected_display != "--- Select Order ---":
                # Extract Order ID from the beautified string
                selected_id = selected_display.split("—")[0].strip().replace('#', '')
                for o in sorted_orders:
                    if o["order_id"] == selected_id:
                        previous_order = o
                        st.success("✨ Details loaded successfully!")
                        break

        else:
            st.warning(f"No previous orders found for **{customer}**. Proceeding as a new order.")

    # Save the selected previous order data to session state
    st.session_state["previous_order"] = previous_order

    st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------
# STEP 3 — MAIN FORM (Styled with Tabs)
# ------------------------------------------
with st.form("order_form", clear_on_submit=True):
    
    st.header("3️⃣ Order Specification Form")
    st.caption("Fill in the details. Fields are auto-filled if a repeat order was selected.")
    st.divider()

    order_id = generate_order_id()
    st.text_input("Order ID (System Generated)", order_id, disabled=True)

    prev = st.session_state.get("previous_order", {}) # Use an empty dict as default for simpler indexing

    tab1, tab2 = st.tabs(["📋 General & Timeline", "📐 Specification IDs & Rate"])

    with tab1:
        st.subheader("Core Product Details")
        
        # Determine initial values
        default_pt = prev.get("product_type", "Bag")
        default_qty = int(prev.get("qty", 100))
        default_priority = prev.get("priority", "Medium")

        colA, colB, colC = st.columns(3)
        with colA:
            product_type = st.selectbox(
                "Product Type",
                ["Bag", "Box"],
                index=["Bag","Box"].index(default_pt) if default_pt in ["Bag", "Box"] else 0,
                help="Determines the next manufacturing step (Assembly for Bag, DieCut for Box)."
            )
        with colB:
            qty = st.number_input(
                "Quantity (Units)",
                min_value=1,
                value=default_qty
            )
        with colC:
            priority = st.selectbox(
                "Priority Level",
                ["High", "Medium", "Low"],
                index=["High","Medium","Low"].index(default_priority) if default_priority in ["High", "Medium", "Low"] else 1
            )

        item = st.text_area(
            "Product Description (Required)",
            value=prev.get("item", ""),
            height=100,
            placeholder="e.g., Luxury matte black shopping bag with rope handles."
        )
        
        st.markdown("---")
        st.subheader("Timeline & Payment")
        
        default_due_date = date.today()
        if prev.get("due"):
            try:
                default_due_date = date.fromisoformat(prev["due"])
            except:
                pass # Use today's date if parsing fails

        colD, colE = st.columns(2)
        with colD:
            receive_date = st.date_input("Order Received Date", value=date.today())
        with colE:
            due_date = st.date_input("Target Due Date", value=default_due_date)

        default_advance_index = 0 if prev.get("advance") == "Yes" else 1
        advance = st.radio(
            "Advance Payment Received?",
            ["Yes", "No"],
            index=default_advance_index,
            horizontal=True
        )

    with tab2:
        st.subheader("Manufacturing Specification IDs")
        
        # Group spec IDs into two columns for better density
        colF, colG = st.columns(2)

        with colF:
            foil = st.text_input("Foil Printing ID", value=prev.get("foil_id",""), placeholder="e.g., F-1234")
            brand_thickness = st.text_input("Brand Thickness ID", value=prev.get("brand_thickness_id",""), placeholder="e.g., BT-250GSM")
            size = st.text_input("Size ID (Dimensions)", value=prev.get("size_id",""), placeholder="e.g., S-A3")
        
        with colG:
            spotuv = st.text_input("Spot UV ID", value=prev.get("spotuv_id",""), placeholder="e.g., UV-5678")
            paper_thickness = st.text_input("Paper Thickness ID", value=prev.get("paper_thickness_id",""), placeholder="e.g., PT-100GSM")
            
            # Rate input and dynamic calculation feedback
            rate = st.number_input(
                "Rate (Unit Price ₹)", 
                min_value=0.0, 
                value=float(prev.get("rate", 0.0)),
                format="%.2f"
            )
            
        # --- Final Summary Metric ---
        total_value = float(qty) * float(rate)
        st.markdown("---")
        st.metric(
            label="💰 Estimated Total Order Value (Quantity × Rate)", 
            value=f"₹{total_value:,.2f}"
        )

    # ------------------------------------------
    # SUBMIT BUTTON
    # ------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("🚀 Finalize and Create Order", type="primary", use_container_width=True)

    if submitted:
        # Final validation before saving
        if not customer:
            st.error("❌ **Customer name is missing.** Please fill in Step 1.")
        elif not item.strip():
            st.error("❌ **Product description is required.** Please fill in Tab 1.")
        elif receive_date > due_date:
            st.error("❌ **Due Date cannot be before the Received Date.** Please check the dates in Tab 1.")
        else:
            # Data preparation and saving
            next_stage = "DieCut" if product_type == "Box" else "Assembly"
            
            # Clean and standardize data
            data = {
                "order_id": order_id,
                "customer": customer,
                "type": order_type_simple, # Use 'New' or 'Repeat'
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
                st.success(f"✅ Order **{order_id}** for **{customer}** created successfully! Moving to the **Design** stage.")
                st.balloons()
                # Optional: Clear session state to reset repeat selection for the next order
                st.session_state["previous_order"] = None
            except Exception as e:
                st.exception(f"An error occurred while saving to the database: {e}")
