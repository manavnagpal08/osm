import streamlit as st
from firebase import push, read
from utils import generate_order_id

# -----------------------------
# ROLE CHECK
# -----------------------------
if "role" not in st.session_state:
    st.switch_page("pages/login.py")

# Only admin + design department can create orders
if st.session_state["role"] not in ["admin", "design"]:
    st.error("❌ You do not have permission to access this page.")
    st.stop()

st.title("📦 Create New Order")

st.write("Fill the details below to create a new manufacturing order.")

# -----------------------------
# AUTO ORDER ID (SRP001...)
# -----------------------------
order_id = generate_order_id()
st.text_input("Order ID", order_id, disabled=True)

# -----------------------------
# ORDER FORM FIELDS
# -----------------------------
customer = st.text_input("Customer Name")
item = st.text_area("Product Description")
qty = st.number_input("Quantity", min_value=1)

col1, col2 = st.columns(2)
with col1:
    receive_date = st.date_input("Order Received Date")
with col2:
    due_date = st.date_input("Due Date")

st.subheader("Additional Order Information")

col3, col4 = st.columns(2)
with col3:
    new_or_repeat = st.selectbox("Order Type", ["New", "Repeat"])
with col4:
    advance = st.radio("Advance Received?", ["Yes", "No"])

foil = st.text_input("Foil Printing ID (optional)")
spotuv = st.text_input("Spot UV ID (optional)")
brand_thickness = st.text_input("Brand Thickness / Quality ID (optional)")
paper_thickness = st.text_input("Paper Thickness / Quality ID (optional)")
size = st.text_input("Size ID (optional)")
rate = st.number_input("Rate (optional)", min_value=0.0)

# -----------------------------
# SUBMIT BUTTON
# -----------------------------
if st.button("Create Order", type="primary", use_container_width=True):

    # Validation
    if not customer or not item or qty <= 0:
        st.error("⚠️ Please fill all required fields.")
        st.stop()

    # Order payload
    data = {
        "order_id": order_id,
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
        "stage": "Design",       # All new orders go to design first
        "status_history": {
            "created_by": st.session_state["username"],
            "created_role": st.session_state["role"],
        }
    }

    # Save to Firebase
    push("orders", data)

    st.success(f"✅ Order **{order_id}** created successfully!")
    st.balloons()

