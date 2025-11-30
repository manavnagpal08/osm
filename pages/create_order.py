import streamlit as st
from firebase import read, push
from utils import generate_order_id
from datetime import date # Import date for default date inputs

# --- CONFIGURATION ---
# Set wide layout and page title for better use of screen space
st.set_page_config(layout="wide", page_title="Create Order", page_icon="📦")

# ------------------------------------------
# MOCK FIREBASE/UTILS FUNCTIONS (Required for running standalone)
# NOTE: You MUST replace these with your actual Firebase integration code.
# ------------------------------------------
# Assuming 'firebase' module provides read/push and 'utils' provides ID generation

# --- MOCK DATA/FUNCTIONS START ---
MOCK_ORDERS_DB = {
    "ord001": {"order_id": "ORD001", "customer": "Acme Corp", "type": "New", "product_type": "Bag", "priority": "Medium", "item": "Standard Yellow Bag", "qty": 500, "received": "2025-10-01", "due": "2025-10-15", "advance": "No", "foil_id": "F-A1", "spotuv_id": "", "brand_thickness_id": "BT-250", "paper_thickness_id": "PT-100GSM", "size_id": "S-SM", "rate": 5.50, "stage": "Printing", "next_after_printing": "Assembly"},
    "ord002": {"order_id": "ORD002", "customer": "Beta Solutions", "type": "New", "product_type": "Box", "priority": "High", "item": "Premium Black Gift Box", "qty": 100, "received": "2025-10-05", "due": "2025-10-12", "advance": "Yes", "foil_id": "F-B2", "spotuv_id": "UV-205", "brand_thickness_id": "BT-350", "paper_thickness_id": "PT-150GSM", "size_id": "S-LGE", "rate": 12.00, "stage": "Design", "next_after_printing": "DieCut"},
    "ord003": {"order_id": "ORD003", "customer": "Acme Corp", "type": "Repeat", "product_type": "Bag", "priority": "Medium", "item": "Custom Blue Logo Bag", "qty": 1000, "received": "2025-11-01", "due": "2025-11-20", "advance": "Yes", "foil_id": "F-C3", "spotuv_id": "", "brand_thickness_id": "BT-250", "paper_thickness_id": "PT-100GSM", "size_id": "S-MED", "rate": 6.25, "stage": "Assembly", "next_after_printing": "Assembly"}
}

# Replace with your actual implementation
def read(collection_name):
    if collection_name == "orders":
        return MOCK_ORDERS_DB
    return {}

# Replace with your actual implementation
def push(collection_name, data):
    # In a real app, this would push to Firebase
    print(f"--- PUSHING TO {collection_name} ---")
    print(data)
    # Simulate adding to mock DB
    key = data["order_id"]
    MOCK_ORDERS_DB[key] = data

# Replace with your actual implementation
def generate_order_id():
    import random
    import string
    # Generate a simple 5-digit ID for demonstration
    return ''.join(random.choices(string.digits, k=5))
# --- MOCK DATA/FUNCTIONS END ---


# ------------------------------------------
# ROLE CHECK
# ------------------------------------------
# NOTE: Ensure you have a "pages/login.py" file and a functioning role check.
if "role" not in st.session_state:
    # st.switch_page("pages/login.py") # Uncomment this line in your final app
    # MOCKING LOGIN FOR DEMO:
    st.session_state["role"] = "design"

if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Manufacturing Order")
st.caption("Efficiently log new and repeat customer orders with auto-fill capabilities.")

# Load all orders first
all_orders = read("orders") or {}
# Extract unique customer names from past orders
customer_list = sorted(list(set(
    o.get("customer", "") for o in all_orders.values() if isinstance(o, dict)
)))

# Initialize state for previous order data to manage auto-filling
if 'previous_order' not in st.session_state:
    st.session_state['previous_order'] = None

# ------------------------------------------
# Order Form Setup
# ------------------------------------------
with st.form("new_order_form", clear_on_submit=True): # clear_on_submit=True resets the form after success

    # --- Order ID ---
    order_id = generate_order_id()
    st.session_state['generated_order_id'] = order_id
    st.text_input("Order ID (Auto-Generated)", order_id, disabled=True, help="Unique identifier for this order.")

    # --- TABS FOR BETTER FLOW ---
    tab1, tab2, tab3 = st.tabs(["👤 Customer & Order Type", "📝 Product Details", "📐 Specifications & Rate"])

    with tab1:
        st.subheader("Customer Selection")

        # Use a radio for primary order type selection for clear distinction
        order_type = st.radio(
            "Is this a **New** or **Repeat** order?",
            ["New", "Repeat"],
            key="order_type_select",
            horizontal=True
        )

        customer = None
        previous_order_data = None # This will hold the dict of the selected previous order

        if order_type == "New":
            customer = st.text_input("Enter **New** Customer Name", key="new_customer_name", placeholder="e.g., Jane Doe Inc.")
            st.info("💡 For new customers, all fields must be filled manually.")

        else:  # Repeat order
            if customer_list:
                customer = st.selectbox("Select Existing Customer", customer_list, key="repeat_customer_select")
            else:
                st.warning("No existing customers found. Please select 'New Order'.")
                customer = None 

            if customer:
                # Once customer selected → fetch previous orders
                customer_orders = {
                    key: o for key, o in all_orders.items()
                    if isinstance(o, dict) and o.get("customer") == customer
                }

                if customer_orders:
                    # Sort orders by date for better context
                    sorted_orders = sorted(
                        customer_orders.values(),
                        key=lambda x: x.get('received', '0000-00-00'), # Sort by received date
                        reverse=True
                    )
                    
                    # Create descriptive options showing ID, Item, and Date
                    order_options = [f"#{o['order_id']} — {o['item']} (Rec: {o['received']})" for o in sorted_orders]
                    
                    selected_order_display = st.selectbox(
                        "Select Previous Order to Auto-Fill Details",
                        ["--- Select an order to load details ---"] + order_options
                    )

                    # Identify the selected previous order object
                    if selected_order_display != "--- Select an order to load details ---":
                        selected_order_id = selected_order_display.split('—')[0].strip().replace('#', '')
                        for o in sorted_orders:
                            if o["order_id"] == selected_order_id:
                                previous_order_data = o
                                break
                    
                    st.session_state['previous_order'] = previous_order_data
                else:
                    st.warning(f"No previous orders found for **{customer}**.")
                    st.session_state['previous_order'] = None
            else:
                st.session_state['previous_order'] = None
    
    # Update previous_order reference based on session state for auto-filling
    previous_order = st.session_state.get('previous_order')

    with tab2:
        st.subheader("Core Order Information")
        
        # Determine initial values based on previous_order data
        default_product_type = previous_order.get("product_type", "Bag") if previous_order and previous_order.get("product_type") in ["Bag", "Box"] else "Bag"
        default_priority = previous_order.get("priority", "Medium") if previous_order and previous_order.get("priority") in ["High", "Medium", "Low"] else "Medium"
        default_qty = int(previous_order.get("qty", 100)) if previous_order else 100
        default_item = previous_order.get("item", "") if previous_order else ""
        
        col1_t2, col2_t2, col3_t2 = st.columns(3)
        with col1_t2:
            product_type = st.selectbox(
                "Product Type",  
                ["Bag", "Box"],  
                index=["Bag","Box"].index(default_product_type),
                help="Determines the next stage in the manufacturing workflow."
            )
        with col2_t2:
            qty = st.number_input("Quantity", min_value=1, value=default_qty)
        with col3_t2:
            priority = st.selectbox(
                "Priority",
                ["High", "Medium", "Low"],
                index=["High","Medium","Low"].index(default_priority),
                help="Sets the urgency for manufacturing stages."
            )

        item = st.text_area(
            "Product Description / Item Name (Required)",
            value=default_item,
            placeholder="e.g., Luxury Matt Black Shopping Bag, 5x5x2 Shipping Box",
            height=100
        )
        
        st.markdown("---")
        st.subheader("Timeline & Finance")
        
        col1_t2_date, col2_t2_date = st.columns(2)
        with col1_t2_date:
            receive_date = st.date_input("Order Received Date", value=date.today())
        with col2_t2_date:
            # Set default due date (Today's date, or loaded from previous order)
            default_due = date.today()
            if previous_order and previous_order.get("due"):
                try:
                    default_due = date.fromisoformat(previous_order.get("due"))
                except ValueError:
                    # Fallback to today if date format is bad
                    pass 
            due_date = st.date_input("Due Date (Target Completion)", value=default_due)

        default_advance_index = 0 if previous_order and previous_order.get("advance") == "Yes" else 1
        advance = st.radio(
            "Advance Payment Received?", 
            ["Yes", "No"], 
            index=default_advance_index,
            horizontal=True
        )

    with tab3:
        st.subheader("Specification Details (IDs/References)")
        st.info("These IDs link to detailed design and material specifications for manufacturing.")
        
        # Use columns for a compact, spreadsheet-like layout
        col1_t3, col2_t3 = st.columns(2)

        with col1_t3:
            foil = st.text_input("Foil Printing ID",
                                 value=previous_order.get("foil_id","") if previous_order else "",
                                 placeholder="e.g., F-101")
            
            brand_thickness = st.text_input("Brand Thickness ID",
                                             value=previous_order.get("brand_thickness_id","") if previous_order else "",
                                             placeholder="e.g., BT-250")

            size = st.text_input("Size ID (Dimensions)",
                                 value=previous_order.get("size_id","") if previous_order else "",
                                 placeholder="e.g., S-A4")
        
        with col2_t3:
            spotuv = st.text_input("Spot UV ID",
                                   value=previous_order.get("spotuv_id","") if previous_order else "",
                                   placeholder="e.g., UV-205")

            paper_thickness = st.text_input("Paper Thickness ID",
                                             value=previous_order.get("paper_thickness_id","") if previous_order else "",
                                             placeholder="e.g., PT-120GSM")

            default_rate = float(previous_order.get("rate",0.0)) if previous_order else 0.0
            rate = st.number_input("Rate (per unit)",
                                   min_value=0.0,
                                   value=default_rate,
                                   format="%.2f",
                                   help="Selling price per unit of product."
            )

        st.markdown("---")
        total_value = float(qty) * float(rate)
        st.metric(label="Estimated Order Value", value=f"₹{total_value:,.2f}", delta="Calculated from Quantity × Rate")


    # ------------------------------------------
    # SAVE BUTTON & VALIDATION
    # ------------------------------------------
    st.markdown("---")
    submitted = st.form_submit_button("✅ Create Order & Move to Design Stage", type="primary", use_container_width=True)

    if submitted:
        # Get final values for validation and data creation
        final_customer = customer.strip() if customer else ""
        final_item = item.strip() if item else ""
        
        # Client-side validation
        if not final_customer:
            st.error("⚠️ **Customer name is required.** Please complete Tab 1.")
        elif not final_item:
            st.error("⚠️ **Product Description / Item Name is required.** Please complete Tab 2.")
        elif receive_date > due_date:
            st.error("⚠️ **Due Date cannot be before the Received Date.** Please check your dates in Tab 2.")
        else:
            # Determine the next stage after the initial 'Design' stage
            next_route = "DieCut" if product_type == "Box" else "Assembly"

            data = {
                "order_id": order_id,
                "customer": final_customer,
                "type": order_type,
                "product_type": product_type,
                "priority": priority,

                "item": final_item,
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

                "stage": "Design", # All orders start at the design stage
                "next_after_printing": next_route
            }

            # Database push
            try:
                push("orders", data)
                st.success(f"Order **{order_id}** for **{final_customer}** created successfully! 🎉")
                st.info(f"The order has been placed in the **Design** stage. The form is now reset.")
                st.balloons()
            except Exception as e:
                st.error(f"Failed to save order: {e}")
